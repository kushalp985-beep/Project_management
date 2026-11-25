# -*- coding: utf-8 -*-
import json

from odoo import _, api, models
from odoo.exceptions import UserError


class UnitSummaryReport(models.AbstractModel):
    _name = 'report.bliss_property_management.unit_summary_report'
    _description = 'Unit Summary PDF Report'

    @api.model
    def _parse_report_data(self, data):
        result = dict(data or {})
        for key in ('contract_ids', 'record_ids'):
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
        if isinstance(result.get('totals'), str):
            try:
                result['totals'] = json.loads(result['totals'])
            except (json.JSONDecodeError, TypeError, ValueError):
                result['totals'] = {}
        if isinstance(result.get('lines'), str):
            try:
                result['lines'] = json.loads(result['lines'])
            except (json.JSONDecodeError, TypeError, ValueError):
                result['lines'] = []
        return result

    @api.model
    def _resolve_report_payload(self, docids, data):
        data = self._parse_report_data(data)
        docids = docids or data.get('contract_ids') or data.get('record_ids') or []
        contracts = self.env['property.contract'].browse(docids).exists()

        wizard = self.env['unit.summary.report.wizard'].browse(
            data.get('wizard_id')
        ).exists()

        lines = data.get('lines') or []
        totals = data.get('totals') or {}

        if wizard and (not lines or not totals):
            contracts = wizard._get_contracts() if not contracts else contracts
            lines = wizard._get_report_lines(contracts)
            totals = wizard._get_totals(lines)

        if not contracts and lines:
            contract_ids = [
                line['contract_id']
                for line in lines
                if line.get('contract_id')
            ]
            contracts = self.env['property.contract'].browse(contract_ids).exists()

        if not lines and contracts:
            wizard_model = self.env['unit.summary.report.wizard']
            lines = wizard_model._get_report_lines(contracts)
            totals = wizard_model._get_totals(lines)

        if not lines:
            raise UserError(_('No records selected for Unit Summary Report.'))

        if not totals:
            totals = {
                'total_paid': sum(line.get('paid_amount', 0) for line in lines),
                'total_unpaid': sum(line.get('unpaid_amount', 0) for line in lines),
                'total_management_fee': sum(
                    line.get('management_fee', 0) for line in lines
                ),
                'show_management_fee': any(
                    line.get('maintenance_billing') == 'separate' for line in lines
                ),
            }

        return contracts, lines, totals, data, wizard

    @api.model
    def _format_line_amounts(self, contracts, lines):
        contract_by_id = {c.id: c for c in contracts}
        formatted = []
        for line in lines:
            contract = contract_by_id.get(line.get('contract_id'))
            currency_contract = contract or contracts[:1]
            format_amount = (
                currency_contract.format_report_currency
                if currency_contract else lambda amount: amount
            )
            formatted.append({
                'building_name': line.get('building_name', ''),
                'unit_name': line.get('unit_name', ''),
                'management_fee_display': (
                    format_amount(line.get('management_fee', 0))
                    if line.get('maintenance_billing') == 'separate' else ''
                ),
                'paid_display': format_amount(line.get('paid_amount', 0)),
                'unpaid_display': format_amount(line.get('unpaid_amount', 0)),
            })
        return formatted

    @api.model
    def _get_report_values(self, docids, data=None):
        contracts, lines, totals, data, wizard = self._resolve_report_payload(docids, data)
        format_contract = contracts[:1]
        format_amount = (
            format_contract.format_report_currency
            if format_contract else lambda amount: amount
        )
        show_management_fee = totals.get('show_management_fee')
        if show_management_fee is None:
            show_management_fee = any(
                line.get('maintenance_billing') == 'separate' for line in lines
            )
        return {
            'doc_ids': contracts.ids,
            'doc_model': 'property.contract',
            'docs': contracts,
            'lines': self._format_line_amounts(contracts, lines),
            'totals': {
                'total_paid_display': format_amount(totals.get('total_paid', 0)),
                'total_unpaid_display': format_amount(totals.get('total_unpaid', 0)),
                'total_management_fee_display': format_amount(
                    totals.get('total_management_fee', 0)
                ),
            },
            'show_management_fee': show_management_fee,
            'report_title': data.get('report_title', 'Unit Summary Report'),
            'building_label': wizard.building_id.name if wizard and wizard.building_id else '',
            'project_label': wizard.project_id.name if wizard and wizard.project_id else '',
            'owner_label': wizard.owner_id.name if wizard and wizard.owner_id else '',
            'unit_label': (
                wizard.unit_id.display_name
                if wizard and wizard.unit_id else ''
            ),
        }
