# -*- coding: utf-8 -*-
import io
import base64
import xlsxwriter

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class UnitSummaryReportWizard(models.TransientModel):
    _name = 'unit.summary.report.wizard'
    _description = 'Unit Summary Report Wizard'

    project_id = fields.Many2one('property.project', string='Project')
    building_id = fields.Many2one(
        'property.building',
        string='Building',
        domain="[('project_id', '=', project_id)]",
    )
    owner_id = fields.Many2one(
        'res.partner',
        string='Owner',
        domain=[('contact_type', '=', 'owner')],
    )
    unit_id = fields.Many2one(
        'property.unit',
        string='Unit',
        domain="['|', ('building_id', '=', building_id), ('building_id.project_id', '=', project_id)]",
    )

    xlsx_file = fields.Binary(string='Excel File', attachment=False)
    xlsx_filename = fields.Char(string='Excel Filename')

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.building_id and self.building_id.project_id != self.project_id:
            self.building_id = False
        if self.unit_id and (
            (self.building_id and self.unit_id.building_id != self.building_id)
            or (self.project_id and self.unit_id.building_id.project_id != self.project_id)
        ):
            self.unit_id = False
        if self.project_id:
            self.owner_id = self.project_id.owner_id

    @api.onchange('building_id')
    def _onchange_building_id(self):
        if self.unit_id and self.unit_id.building_id != self.building_id:
            self.unit_id = False

    def _get_search_domain(self):
        self.ensure_one()
        domain = []
        if self.project_id:
            domain.append(('project_id', '=', self.project_id.id))
        if self.building_id:
            domain.append(('building_id', '=', self.building_id.id))
        if self.owner_id:
            domain.append(('owner_id', '=', self.owner_id.id))
        if self.unit_id:
            domain.append(('unit_id', '=', self.unit_id.id))
        return domain

    def _pick_primary_contract_per_unit(self, contracts):
        by_unit = {}
        for contract in contracts:
            unit = contract.unit_id
            if not unit:
                continue
            existing = by_unit.get(unit.id)
            if not existing:
                by_unit[unit.id] = contract
                continue
            if contract.state == 'signed' and existing.state != 'signed':
                by_unit[unit.id] = contract
            elif contract.state == existing.state and (
                (contract.date_start or contract.date) > (existing.date_start or existing.date)
            ):
                by_unit[unit.id] = contract
        return self.env['property.contract'].browse([c.id for c in by_unit.values()])

    def _get_contracts(self):
        self.ensure_one()
        contracts = self.env['property.contract'].search(
            self._get_search_domain(),
            order='building_id, unit_id, date_start desc, id desc',
        )
        contracts = self._pick_primary_contract_per_unit(contracts)
        if not contracts:
            raise UserError(_('No matching units/contracts found for the selected filters.'))
        return contracts.sorted(key=lambda c: (
            c.building_id.name or '',
            c.unit_id.name or c.unit_id.unit_no or '',
        ))

    def _get_report_lines(self, contracts):
        lines = []
        for contract in contracts:
            unit = contract.unit_id
            maintenance_billing = contract.maintenance_billing or ''
            lines.append({
                'building_name': contract.building_id.name or '',
                'unit_name': unit.name or unit.unit_no or '',
                'maintenance_billing': maintenance_billing,
                'management_fee': (
                    contract.management_fee
                    if maintenance_billing == 'separate' else 0.0
                ),
                'paid_amount': contract.total_paid,
                'unpaid_amount': contract.to_be_paid,
                'contract_id': contract.id,
            })
        return lines

    def _get_totals(self, lines):
        return {
            'total_paid': sum(line['paid_amount'] for line in lines),
            'total_unpaid': sum(line['unpaid_amount'] for line in lines),
            'total_management_fee': sum(line['management_fee'] for line in lines),
            'show_management_fee': any(
                line.get('maintenance_billing') == 'separate' for line in lines
            ),
        }

    def action_print_pdf(self):
        self.ensure_one()
        contracts = self._get_contracts()
        lines = self._get_report_lines(contracts)
        totals = self._get_totals(lines)
        return self.env.ref(
            'bliss_property_management.action_unit_summary_report'
        ).report_action(
            contracts,
            data={
                'wizard_id': self.id,
                'contract_ids': contracts.ids,
                'lines': lines,
                'totals': totals,
                'report_title': 'Unit Summary Report',
            },
        )

    def action_print_xlsx(self):
        self.ensure_one()

        contracts = self._get_contracts()
        lines = self._get_report_lines(contracts)
        totals = self._get_totals(lines)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Unit Summary')

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
        })
        header_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'bg_color': '#D9EAF7',
        })
        cell_format = workbook.add_format({'border': 1})
        amount_format = workbook.add_format({
            'border': 1,
            'num_format': '#,##0.00',
        })
        total_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'num_format': '#,##0.00',
        })

        show_management_fee = totals['show_management_fee']

        headers = ['Building', 'Unit']
        if show_management_fee:
            headers.append('Management Fee')
        headers.extend(['Paid Amount', 'Unpaid Amount'])

        sheet.merge_range(0, 0, 0, len(headers) - 1,
                          'Unit Summary Report', title_format)

        for col, header in enumerate(headers):
            sheet.write(2, col, header, header_format)

        row = 3
        for line in lines:
            col = 0
            sheet.write(row, col, line['building_name'], cell_format)
            col += 1
            sheet.write(row, col, line['unit_name'], cell_format)
            col += 1

            if show_management_fee:
                sheet.write_number(
                    row, col, line['management_fee'], amount_format
                )
                col += 1

            sheet.write_number(row, col, line['paid_amount'], amount_format)
            col += 1
            sheet.write_number(row, col, line['unpaid_amount'], amount_format)
            row += 1

        sheet.write(row, 0, 'Total', header_format)

        if show_management_fee:
            sheet.write_number(
                row, 2, totals['total_management_fee'], total_format
            )
            paid_col, unpaid_col = 3, 4
        else:
            paid_col, unpaid_col = 2, 3

        sheet.write_number(row, paid_col, totals['total_paid'], total_format)
        sheet.write_number(row, unpaid_col, totals['total_unpaid'], total_format)

        sheet.set_column(0, 1, 22)
        sheet.set_column(2, len(headers) - 1, 18)

        workbook.close()
        output.seek(0)

        filename = 'Unit_Summary_Report.xlsx'
        self.write({
            'xlsx_file': base64.b64encode(output.read()),
            'xlsx_filename': filename,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': (
                '/web/content?model=unit.summary.report.wizard'
                '&id=%s&field=xlsx_file&filename_field=xlsx_filename'
                '&download=true' % self.id
            ),
            'target': 'self',
        }
