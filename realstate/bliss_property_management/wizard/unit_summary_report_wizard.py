# -*- coding: utf-8 -*-
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
