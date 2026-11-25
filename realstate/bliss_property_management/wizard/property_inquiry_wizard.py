# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class PropertyInquiryWizard(models.TransientModel):
    _name = 'property.inquiry.wizard'
    _description = 'Unit Records Report Wizard'

    search_mode = fields.Selection(
        [
            ('unit_wise', 'Unit Wise'),
            ('owner_wise', 'Owner Wise'),
            ('tenant_wise', 'Tenant Wise'),
        ],
        string='Search Mode',
        default='unit_wise',
        required=True,
    )
    unit_id = fields.Many2one('property.unit', string='Unit')
    owner_id = fields.Many2one(
        'res.partner',
        string='Owner',
        domain=[('contact_type', '=', 'owner')],
    )
    tenant_id = fields.Many2one(
        'res.partner',
        string='Tenant',
        domain=[('contact_type', '=', 'tenant')],
    )
    building_id = fields.Many2one('property.building', string='Building')
    floor_no = fields.Char(string='Floor')
    contract_status = fields.Selection(
        selection=lambda self: self.env['property.contract']._fields['state'].selection,
        string='Contract Status',
    )
    payment_status = fields.Selection(
        [
            ('all', 'All'),
            ('paid', 'Paid'),
            ('partial', 'Partially Paid'),
            ('unpaid', 'Unpaid'),
        ],
        string='Payment Status',
        default='all',
        required=True,
    )
    cheque_status = fields.Selection(
        selection=lambda self: self.env['account.cheque']._fields['status1'].selection,
        string='Cheque Status',
    )
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')

    @api.onchange('search_mode')
    def _onchange_search_mode(self):
        if self.search_mode == 'unit_wise':
            self.owner_id = False
            self.tenant_id = False
        elif self.search_mode == 'owner_wise':
            self.unit_id = False
            self.tenant_id = False
        elif self.search_mode == 'tenant_wise':
            self.unit_id = False
            self.owner_id = False

    @api.onchange('building_id')
    def _onchange_building_id(self):
        if self.unit_id and self.unit_id.building_id != self.building_id:
            self.unit_id = False

    @api.onchange('owner_id')
    def _onchange_owner_id(self):
        if self.owner_id and self.building_id and self.building_id.owner_id != self.owner_id:
            self.building_id = False

    def _validate_required_selection(self):
        self.ensure_one()
        if self.search_mode == 'unit_wise' and not self.unit_id:
            raise UserError(_('Please select a Unit for Unit Wise search.'))
        if self.search_mode == 'owner_wise' and not self.owner_id:
            raise UserError(_('Please select an Owner for Owner Wise search.'))
        if self.search_mode == 'tenant_wise' and not self.tenant_id:
            raise UserError(_('Please select a Tenant for Tenant Wise search.'))

    def _get_base_domain(self):
        self.ensure_one()
        domain = []
        if self.search_mode == 'unit_wise':
            domain.append(('unit_id', '=', self.unit_id.id))
        elif self.search_mode == 'tenant_wise':
            domain.append(('partner_id', '=', self.tenant_id.id))
        elif self.search_mode == 'owner_wise':
            domain.append(('owner_id', '=', self.owner_id.id))

        if self.unit_id and self.search_mode != 'unit_wise':
            domain.append(('unit_id', '=', self.unit_id.id))
        if self.tenant_id and self.search_mode != 'tenant_wise':
            domain.append(('partner_id', '=', self.tenant_id.id))
        if self.owner_id and self.search_mode != 'owner_wise':
            domain.append(('owner_id', '=', self.owner_id.id))
        if self.building_id:
            domain.append(('building_id', '=', self.building_id.id))
        if self.floor_no:
            domain.append(('unit_id.floor_no', '=', self.floor_no))
        if self.contract_status:
            domain.append(('state', '=', self.contract_status))
        return domain

    def _pick_primary_contract_per_unit(self, contracts):
        """Keep one contract per unit: prefer signed, then latest start date."""
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

    def _match_payment_status(self, contract):
        self.ensure_one()
        if self.payment_status == 'all':
            return True
        currency = contract.contract_currency_id
        rounding = currency.rounding if currency else 0.01
        if self.payment_status == 'paid':
            return float_is_zero(contract.to_be_paid, precision_rounding=rounding)
        if self.payment_status == 'unpaid':
            return float_is_zero(contract.total_paid, precision_rounding=rounding)
        if self.payment_status == 'partial':
            return (
                not float_is_zero(contract.total_paid, precision_rounding=rounding)
                and not float_is_zero(contract.to_be_paid, precision_rounding=rounding)
            )
        return True

    def _match_cheque_status(self, contract):
        self.ensure_one()
        if not self.cheque_status:
            return True
        cheques = contract._get_rent_installment_cheques()
        return any(c.status1 == self.cheque_status for c in cheques)

    def _match_date_range(self, contract):
        self.ensure_one()
        if not self.date_from and not self.date_to:
            return True
        cheques = contract._get_rent_installment_cheques()
        for cheque in cheques:
            if self.date_from and cheque.cheque_date and cheque.cheque_date >= self.date_from:
                return True
            if self.date_to and cheque.cheque_date and cheque.cheque_date <= self.date_to:
                return True
        moves = self.env['account.move'].search([
            ('account_cheque_id', 'in', contract.account_cheque_ids.ids),
            ('state', '=', 'posted'),
        ])
        for move in moves:
            if self.date_from and move.date and move.date >= self.date_from:
                return True
            if self.date_to and move.date and move.date <= self.date_to:
                return True
        return not (self.date_from or self.date_to)

    def _get_contracts(self):
        self.ensure_one()
        self._validate_required_selection()
        contracts = self.env['property.contract'].search(
            self._get_base_domain(),
            order='date_start desc, id desc',
        )
        contracts = self._pick_primary_contract_per_unit(contracts)
        if self.search_mode == 'unit_wise' and not self.contract_status:
            signed = contracts.filtered(lambda c: c.state == 'signed')
            if signed:
                contracts = self._pick_primary_contract_per_unit(signed)
        contracts = contracts.filtered(self._match_payment_status)
        contracts = contracts.filtered(self._match_cheque_status)
        contracts = contracts.filtered(self._match_date_range)
        if not contracts:
            raise UserError(_('No matching property contracts found for the selected filters.'))
        return contracts

    def action_print_pdf(self):
        self.ensure_one()
        contracts = self._get_contracts()
        return self.env.ref(
            'bliss_property_management.action_property_inquiry_report'
        ).report_action(
            contracts,
            data={
                'wizard_id': self.id,
                'contract_ids': contracts.ids,
                'search_mode': self.search_mode,
                'date_from': self.date_from,
                'date_to': self.date_to,
            },
        )
