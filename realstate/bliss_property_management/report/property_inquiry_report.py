# -*- coding: utf-8 -*-
import json

from odoo import _, api, models
from odoo.exceptions import UserError
import io
import base64
import xlsxwriter


class PropertyInquiryReport(models.AbstractModel):
    _name = 'report.bliss_property_management.property_inquiry'
    _description = 'Unit Records PDF Report'

    @api.model
    def _parse_report_data(self, data):
        result = dict(data or {})
        for key in ('record_ids', 'contract_ids'):
            val = result.get(key)
            if isinstance(val, str):
                try:
                    result[key] = json.loads(val)
                except (json.JSONDecodeError, TypeError, ValueError):
                    if val:
                        result[key] = [
                            int(x) for x in val.split(',') if str(x).strip().isdigit()
                        ]
        if isinstance(result.get('wizard_id'), str):
            try:
                result['wizard_id'] = int(result['wizard_id'])
            except ValueError:
                pass
        return result

    @api.model
    def _resolve_contracts(self, docids, data):
        """Resolve contracts from docids, explicit data payload, or wizard."""
        data = self._parse_report_data(data)
        docids = docids or data.get('contract_ids') or data.get('record_ids') or []
        contracts = self.env['property.contract'].browse(docids).exists()
        if contracts:
            return contracts, data

        wizard = self.env['property.inquiry.wizard'].browse(
            data.get('wizard_id')
        ).exists()
        if wizard:
            return wizard._get_contracts(), data

        return contracts, data

    @api.model
    def _build_page(self, contract):
        unit = contract.unit_id
        financial = contract._get_inquiry_financial_summary()
        renewals = contract.env['contract.renewal'].search(
            [('contract_id', '=', contract.id)],
            order='id desc',
        )
        state_labels = dict(contract._fields['state'].selection)
        return {
            'contract': contract,
            'unit': unit,
            'unit_display_name': contract._get_inquiry_unit_display_name(),
            'tenant_name': contract.partner_id.name,
            'contract_start': contract.date_start,
            'contract_end': contract.date_stop,
            'contract_start_display': contract.format_report_date(contract.date_start),
            'contract_end_display': contract.format_report_date(contract.date_stop),
            'total_rent': financial['total_rent'],
            'cheque_lines': contract._get_inquiry_cheque_payment_lines(),
            'payment_history': contract._get_inquiry_payment_history(),
            'financial': financial,
            'owner': contract._get_inquiry_owner_details(),
            'tenant': contract._get_inquiry_tenant_details(unit=unit),
            'invoices': contract._get_inquiry_invoice_lines(),
            'maintenance': contract._get_inquiry_maintenance_lines(),
            'timeline': contract._get_inquiry_timeline_events(),
            'documents': contract._get_inquiry_documents(),
            'contract_type': 'Renewal' if contract.is_renew else 'New',
            'contract_state_label': state_labels.get(contract.state, contract.state),
            'renewal_records': renewals,
            'parking_count': unit.building_id.parking_count if unit and unit.building_id else 0,
            'unit_state_label': dict(unit._fields['state'].selection).get(
                unit.state, unit.state
            ) if unit else '',
        }

    @api.model
    def _get_report_values(self, docids, data=None):
        contracts, data = self._resolve_contracts(docids, data)
        if not contracts:
            raise UserError(_('No contracts selected for Unit Records report.'))

        wizard = self.env['property.inquiry.wizard'].browse(
            data.get('wizard_id')
        ).exists()

        pages = [self._build_page(contract) for contract in contracts]
        company = contracts[:1].company_id or self.env.company

        return {
            'doc_ids': contracts.ids,
            'doc_model': 'property.contract',
            'docs': contracts,
            'pages': pages,
            'company': company,
            'report_title': 'Unit Records',
            'search_mode': data.get('search_mode') or (wizard.search_mode if wizard else ''),
            'date_from': data.get('date_from') or (wizard.date_from if wizard else False),
            'date_to': data.get('date_to') or (wizard.date_to if wizard else False),
            'format_amount': lambda contract, amount: contract.format_report_currency(amount),
        }

    @api.model
    def action_print_xlsx(self, contracts):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'bg_color': '#D9EAD3',
        })
        header_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'bg_color': '#D9EAD3',
        })
        cell_format = workbook.add_format({
            'border': 1,
            'text_wrap': True,
            'valign': 'top',
        })

        def write_value(sheet, row, label, value):
            if hasattr(value, '_name') and hasattr(value, 'ids'):
                value = ', '.join(value.mapped('display_name'))

            if isinstance(value, dict):
                for key, val in value.items():
                    row = write_value(
                        sheet, row, f'{label} / {key}', val
                    )
                return row

            if isinstance(value, (list, tuple)):
                for index, val in enumerate(value, 1):
                    row = write_value(
                        sheet, row, f'{label} / {index}', val
                    )
                return row

            if value is None or value is False:
                value = ''
            elif not isinstance(value, (str, int, float, bool)):
                value = str(value)

            sheet.write(row, 0, str(label), header_format)
            sheet.write(row, 1, value, cell_format)
            return row + 1

        for index, contract in enumerate(contracts, 1):
            page = self._build_page(contract)

            sheet = workbook.add_worksheet(f'Unit {index}')
            sheet.set_column('A:A', 35)
            sheet.set_column('B:B', 55)

            sheet.merge_range('A1:B1', 'UNIT RECORDS', title_format)
            sheet.write('A3', 'Information', header_format)
            sheet.write('B3', 'Details', header_format)

            row = 3
            for key, value in page.items():
                row = write_value(
                    sheet,
                    row,
                    key.replace('_', ' ').title(),
                    value,
                )

            sheet.freeze_panes(3, 0)

        workbook.close()
        output.seek(0)

        attachment = self.env['ir.attachment'].create({
            'name': 'Unit_Records.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
