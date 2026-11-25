# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    pdc_cheque = fields.Boolean(string="Allow PDC Option")
    contract_id = fields.Many2one('property.contract', string='Contract')
    inv_contract_id = fields.Many2one('property.contract', string='Contract')
    project_id = fields.Many2one(
        'property.project',
        string='Project',
        compute='_compute_property_dimensions',
        store=True,
        readonly=True,
    )
    unit_id = fields.Many2one(
        'property.unit',
        string='Unit',
        compute='_compute_property_dimensions',
        store=True,
        readonly=True,
    )
    building_id = fields.Many2one(
        'property.building',
        string='Building',
        compute='_compute_property_dimensions',
        store=True,
        readonly=True,
    )

    def _get_linked_contract(self):
        self.ensure_one()
        contract = self.inv_contract_id or self.contract_id
        if not contract and self.account_cheque_id:
            contract = self.account_cheque_id.contract_id
        return contract

    def _get_analytic_distribution(self):
        self.ensure_one()
        contract = self._get_linked_contract()
        if contract:
            return contract._get_invoice_analytic_distribution()
        return False

    def _apply_analytic_distribution_on_lines(self):
        for move in self:
            distribution = move._get_analytic_distribution()
            if not distribution:
                continue
            lines = move.line_ids.filtered(
                lambda line: line.display_type not in ('line_section', 'line_note')
            )
            if lines:
                lines.write({'analytic_distribution': distribution})

    def _is_property_contract_tenant_invoice(self):
        self.ensure_one()
        return (
            self.is_sale_document(include_receipts=True)
            and bool(self._get_linked_contract())
        )

    def _apply_property_contract_tax_line_accounts(self):
        """Apply cheque tax account after standard Odoo tax sync (no grouping-key override)."""
        for move in self.filtered(lambda m: m.state == 'draft'):
            if not move._is_property_contract_tenant_invoice():
                continue
            tax_lines = move.line_ids.filtered('tax_repartition_line_id')
            if not tax_lines:
                continue
            tax_account = move.company_id.cheque_tax_account_id
            if not tax_account:
                raise UserError(_(
                    'Please configure Cheque Tax Account in Account Cheque Configuration.'
                ))
            tax_lines.with_context(skip_invoice_sync=True).write({
                'deferred_start_date': False,
                'deferred_end_date': False,
                'account_id': tax_account.id,
            })

    @contextmanager
    def _sync_tax_lines(self, container):
        with super()._sync_tax_lines(container):
            yield
        container['records']._apply_property_contract_tax_line_accounts()

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._apply_analytic_distribution_on_lines()
        return moves

    def write(self, vals):
        res = super().write(vals)
        if any(key in vals for key in ('inv_contract_id', 'contract_id', 'line_ids', 'account_cheque_id')):
            self._apply_analytic_distribution_on_lines()
        return res

    @api.depends('inv_contract_id', 'inv_contract_id.project_id',
                 'inv_contract_id.unit_id', 'inv_contract_id.building_id',
                 'contract_id', 'contract_id.project_id',
                 'contract_id.unit_id', 'contract_id.building_id')
    def _compute_property_dimensions(self):
        for move in self:
            contract = move._get_linked_contract()
            if contract:
                move.project_id = contract.project_id
                move.unit_id = contract.unit_id
                move.building_id = contract.building_id
            else:
                move.project_id = False
                move.unit_id = False
                move.building_id = False

    @api.model
    def default_get(self, flds):
        result = super(AccountMoveInherit, self).default_get(flds)
        user_company_id = self.env.user.company_id
        result['pdc_cheque'] = user_company_id.pdc_cheque
        return result


class AccountMoveLineInherit(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            if line.analytic_distribution:
                continue
            move = line.move_id
            if not move:
                continue
            distribution = move._get_analytic_distribution()
            if distribution:
                line.analytic_distribution = distribution
        return lines


class AccountJournalInherit(models.Model):
    _inherit = 'account.journal'

    cheque_payment = fields.Boolean(string="Cheque Payment")
