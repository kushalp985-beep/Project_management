import logging

from odoo.exceptions import UserError
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ContractTermination(models.Model):
    _name = "contract.termination"
    _description = "contract termination model"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string="Name", required=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('Contract.term.seq.code'))
    state_term = fields.Selection([
        ('new', 'new'),
        ('bill_check', 'Bill check approved'),
        ('inspection_checked', 'Inspection checked'),
        ('maintenance_inprogress', 'Maintenance in progress'),
        ('tapproved', 'Termination approved'),
        ('done', 'Done'),

    ], tracking=True, copy=False, index=True , default='new')

    contract_id = fields.Many2one('property.contract', string="Contract", readonly=True)
    unit_id = fields.Many2one('property.unit', related="contract_id.unit_id", readonly=True)
    start_date_from = fields.Date(string="Start From", related="contract_id.start_date_from", readonly=True)
    date_start = fields.Date(string="Start Date", related="contract_id.date_start", readonly=True)
    date_stop = fields.Date(string="Stop Date", required=True)
    no_of_days = fields.Integer(string="No. of days", related="contract_id.no_of_days", readonly=True)

    day_value = fields.Monetary(string="Day Value", related="contract_id.day_value", readonly=True,
                                currency_field='contract_currency_id')
    consumed_period = fields.Integer(string="Consumed Period days", compute='_compute_penality', readonly=True)
    consumed_value = fields.Monetary(string="Consumed Value", compute='_compute_penality', readonly=True, currency_field='contract_currency_id')
    balance_period = fields.Integer(string="Balance Period days", compute='_compute_penality', readonly=True)
    balance_value = fields.Monetary(string="Balance Value",compute='_compute_penality', readonly=True, currency_field='contract_currency_id')
    total_paid = fields.Monetary(string="Paid Rent Value", related="contract_id.total_paid", readonly=True,
                                 currency_field='contract_currency_id')
    to_be_paid = fields.Monetary(string="Difference Value", related="contract_id.to_be_paid", readonly=True,
                                 currency_field='contract_currency_id')
    not_paid_cheque_ids = fields.One2many('account.cheque', related="contract_id.not_paid_cheque_ids",
                                          string='Not Paid Cheque')

    excluded_ids = fields.Many2many('property.security.deposit', string="Excluded Security Deposit")
    contract_security_deposit_ids = fields.One2many('property.security.deposit', 'contract_term_id',
                                                    string='Security Deposit')
    termination_type = fields.Selection([
        ("normaltermination", "normal termination"),
        ("earlytermination", "Early termination"),
        ("latetermination", "late termination"),
    ], compute='_compute_termination_type', store=True, readonly=True)

    termination_date = fields.Date(string="Termination date", required=True)

    settlement_amount = fields.Monetary(string="Settlement Amount", readonly=True, compute="_compute_penality", currency_field='contract_currency_id')
    security_deposit = fields.Monetary(string="Security Deposit", readonly=True,
                                    related="contract_id.security_deposit", currency_field='contract_currency_id')
    total_costs = fields.Monetary(string="Total Move Out Process", currency_field='contract_currency_id',related="inspection_cost")
    journal_id = fields.Many2one('account.journal', related="contract_id.journal_id", string="Journal", readonly=True)

    value = fields.Monetary(string="Contract Value", related="contract_id.value", readonly=True, currency_field='contract_currency_id')
    penality_months = fields.Integer(string="Penality Months", compute='_compute_penality', readonly=True)
    penality_amount_per_month = fields.Monetary(string="Penality Amount per Month", compute='_compute_penality',
                                               readonly=True, currency_field='contract_currency_id')
    penality_amount = fields.Monetary(string="Final Penality Amount	", compute='_compute_penality', readonly=True, currency_field='contract_currency_id')
    company_id = fields.Many2one('res.company', related="contract_id.company_id")
    contract_currency_id = fields.Many2one(string='Currency', related="contract_id.contract_currency_id", store=True, readonly=True)
    ijari_canslation_fees = fields.Monetary(string="Ijari cancellation fees", currency_field='contract_currency_id')
    other_cost = fields.Monetary(string="Other Cost", currency_field='contract_currency_id')
    
    
    
    

    is_inspected = fields.Boolean(
        string="Inspected",
        tracking=True,
        default=False
        )

    inspection_cost = fields.Monetary(
        string="Inspection Damage Amount",
        currency_field='contract_currency_id'
    )
    
    inspection_line_ids = fields.One2many(
        'contract.termination.inspection.line',
        'contract_term_id',
        string="Inspection History"
    )


    @api.depends('date_stop', 'contract_id.date_stop')
    def _compute_termination_type(self):
        for record in self:
            scheduled_stop = record.contract_id.date_stop
            actual_stop = record.date_stop
            if scheduled_stop and actual_stop:
                if scheduled_stop == actual_stop:
                    record.termination_type = 'normaltermination'
                elif scheduled_stop > actual_stop:
                    record.termination_type = 'earlytermination'
                else:
                    record.termination_type = 'latetermination'
            else:
                record.termination_type = False


    @api.depends('value', 'date_start', 'date_stop', 'contract_id.date_stop', 'total_costs', 'termination_type',
             'contract_id.penalty_amount')
    def _compute_penality(self):
        for record in self:
            scheduled_stop = record.contract_id.date_stop
            if record.date_stop and record.date_start:
                penality_month_early_termination = 2
                penality_month_late_termination = 30
                penality_month_normal_termination = 0

                consumed_duration = (record.date_stop - record.date_start).days
                balance_period = (record.date_stop - scheduled_stop).days if scheduled_stop else 0

                # Always source penalty amount directly from the contract
                penality_amount = record.contract_id.penalty_amount

                # Initialize variables to safe defaults before branching
                penality_months = 0
                penality_duration = 0
                balance_period_abs = 0

                if record.termination_type == 'latetermination':
                    penality_duration = balance_period + penality_month_late_termination
                    penality_months = penality_duration / 30 if penality_duration else 0
                    balance_period_abs = abs(penality_duration)

                    record.settlement_amount = (
                        (record.total_paid + record.security_deposit)
                        - (consumed_duration * record.day_value)
                        - record.ijari_canslation_fees
                        - record.inspection_cost
                        - penality_amount
                        - record.other_cost
                    )
                    record.balance_period = balance_period_abs
                    record.balance_value = abs(penality_duration * record.day_value)

                elif record.termination_type == 'normaltermination':
                    penality_duration = balance_period + penality_month_normal_termination
                    penality_months = penality_duration / 30 if penality_duration else 0
                    balance_period_abs = abs(penality_duration)

                    record.settlement_amount = (
                        (record.total_paid + record.security_deposit)
                        - (consumed_duration * record.day_value)
                        - record.ijari_canslation_fees
                        - record.inspection_cost
                        - penality_amount
                        - record.other_cost
                    )
                    record.balance_period = balance_period_abs
                    record.balance_value = abs(penality_duration * record.day_value)

                else:  # earlytermination
                    penality_months = penality_month_early_termination
                    penality_duration = penality_month_early_termination * 30
                    balance_period_abs = abs(balance_period)

                    record.settlement_amount = (
                        (record.total_paid + record.security_deposit)
                        - (consumed_duration * record.day_value)
                        - record.ijari_canslation_fees
                        - record.inspection_cost
                        - penality_amount
                        - record.other_cost
                    )
                    record.balance_period = balance_period_abs
                    record.balance_value = abs(balance_period * record.day_value)

                # Assign penalty fields once, after branching logic is complete
                record.penality_amount = penality_amount
                record.penality_months = penality_months
                # record.penality_amount_per_month = (
                #     penality_amount / penality_months if penality_months > 0 else 0
                # )
                record.penality_amount_per_month = 0
                record.consumed_period = consumed_duration
                record.consumed_value = consumed_duration * record.day_value

            else:
                record.penality_months = 0
                record.penality_amount_per_month = 0
                record.penality_amount = 0
                record.consumed_period = 0
                record.consumed_value = 0
                record.balance_period = 0
                record.balance_value = 0
                record.settlement_amount = 0

    # @api.depends('value', 'termination_date', 'date_start', 'date_stop', 'total_costs', 'termination_type')
    # def _compute_penality(self):
    #     for record in self:
    #         if record.termination_date and record.date_stop:
    #             penality_month_early_termination = 2
    #             penality_month_late_termination = 30
    #             penality_month_normal_termination = 0
    #             consumed_duration = (record.termination_date - record.date_start).days
    #             balance_period = (record.termination_date - record.date_stop).days
    #             if record.termination_type == 'latetermination':
    #                 penality_duration = balance_period + penality_month_late_termination
    #                 penality_months = penality_duration / 30
    #                 penality_amount = penality_duration * record.day_value
                    
    #                 # record.settlement_amount = record.total_paid + record.security_deposit - record.consumed_value - record.ijari_canslation_fees - record.inspection_cost - record.penality_amount
    #                 record.settlement_amount = (record.total_paid + record.security_deposit) - (consumed_duration * record.day_value) - record.ijari_canslation_fees - record.inspection_cost - penality_amount - record.other_cost
                    
    #                 # record.settlement_amount = (record.total_paid + record.security_deposit) - (record.consumed_value)
    #                 # + record.ijari_canslation_fees + record.inspection_cost + record.penality_amount + record.other_cost)
    #                 record.balance_period = abs(penality_duration)
    #                 record.balance_value = abs(penality_duration * record.day_value)
    #             elif record.termination_type == 'normaltermination':
    #                 penality_duration = balance_period + penality_month_normal_termination
    #                 penality_months = penality_duration / 30
    #                 penality_amount = penality_duration * record.day_value
    #                 # record.settlement_amount = record.total_paid + record.security_deposit - record.consumed_value - record.ijari_canslation_fees - record.inspection_cost - record.penality_amount
                    
    #                 record.settlement_amount = (record.total_paid + record.security_deposit) - (consumed_duration * record.day_value) - record.ijari_canslation_fees - record.inspection_cost - penality_amount - record.other_cost
                    
    #                 # record.settlement_amount = (record.total_paid + record.security_deposit) - (record.consumed_value)
    #                                                                                             # + record.ijari_canslation_fees + record.inspection_cost + record.penality_amount + record.other_cost)
                    
    #                 record.balance_period = abs(penality_duration)
    #                 record.balance_value = abs(penality_duration * record.day_value)

    #             else:
    #                 penality_months = penality_month_early_termination
    #                 penality_duration = penality_month_early_termination * 30
    #                 penality_amount = penality_duration * record.day_value  
    #                 # record.settlement_amount = record.total_paid + record.security_deposit - record.consumed_value - record.ijari_canslation_fees - record.inspection_cost - record.penality_amount
                    
    #                 record.settlement_amount = (record.total_paid + record.security_deposit) - (consumed_duration * record.day_value) - record.ijari_canslation_fees - record.inspection_cost - penality_amount - record.other_cost
    #                 # + record.ijari_canslation_fees + record.inspection_cost + record.penality_amount + record.other_cost)
                    
    #                 record.balance_period = abs(balance_period)
    #                 record.balance_value = abs(balance_period * record.day_value)

    #             record.penality_amount = penality_amount
    #             record.penality_months = penality_months
    #             record.penality_amount_per_month = penality_amount / penality_months if penality_months > 0 else 0
    #             record.consumed_period = consumed_duration
    #             record.consumed_value = consumed_duration * record.day_value

    #         else:
    #             record.penality_months = 0
    #             record.penality_amount_per_month = 0
    #             record.penality_amount = 0
    #             record.consumed_period = 0
    #             record.consumed_value = 0
    #             record.balance_period = 0
    #             record.balance_value = 0
    #             record.settlement_amount = 0

    def action_approve_termination(self):
        self.write({'state_term': 'tapproved'})
        self.unit_id.status = 'approved'
        self.unit_id.state = "available"

    def action_bill_check(self):
        self.write({'state_term': 'bill_check'})
        
    def action_reset_to_draft(self):
        self.write({'state_term': 'inspection_checked'})
        
        
    move_id = fields.Many2one(
    'account.move',
    string='Settlement Entry',
    readonly=True,
    copy=False
    )

    move_count = fields.Integer(
        string="Journal Entries",
        compute="_compute_move_count"
    )


    def _compute_move_count(self):
        for rec in self:
            rec.move_count = 1 if rec.move_id else 0

            
        


        
        
    # def create_draft_entry(self):
    #     self.ensure_one()

    #     self.write({'state_term': 'done'})
    #     if not self.settlement_amount:
    #         raise UserError(_("Settlement amount is zero. Cannot create journal entry."))

    #     # Get the bank journal (similar to wizard implementation)
    #     bank_journal = self.env['account.journal'].sudo().search([('type', '=', 'bank')], limit=1)
    #     if not bank_journal:
    #         raise UserError(_("No bank journal found. Please configure a bank journal."))

    #     # Create the account move (journal entry)
    #     account_move_obj = self.env['account.move']
    #     move_vals = {
    #         'partner_id': self.contract_id.partner_id.id,
    #         'commercial_partner_id': self.contract_id.partner_id.id,
    #         'date': fields.Datetime.now(),
    #         'journal_id': bank_journal.id,
    #         'company_id': self.contract_id.company_id.id,
    #         'state': 'draft',
    #         'ref': f"Contract Termination Settlement - {self.contract_id.name}",
    #         'inv_contract_id': self.contract_id.id
    #     }

    #     account_move = account_move_obj.create(move_vals)
    #     move_lines = []

    #     # Determine debit and credit accounts based on settlement amount
    #     if self.settlement_amount > 0:
    #         debit_account = self.env['account.account'].search([('code', '=', '100011')], limit=1)
    #         if not debit_account:
    #             raise UserError(_("Accounts Receivable account (100011) not found."))

    #         debit_vals = {
    #             'partner_id': self.contract_id.partner_id.id,
    #             'account_id': debit_account.id,
    #             'debit': self.settlement_amount,
    #             'date_maturity': fields.Date.today(),
    #             'move_id': account_move.id,
    #             'company_id': self.contract_id.company_id.id,
    #         }
    #         move_lines.append((0, 0, debit_vals))

    #         # Credit: Income/Revenue account (500002 - based on penalty charges in wizard)
    #         credit_account = self.env['account.account'].search([('code', '=', '100012')], limit=1)
    #         if not credit_account:
    #             raise UserError(_("Income account (100012) not found."))

    #         credit_vals = {
    #             'partner_id': self.contract_id.partner_id.id,
    #             'account_id': credit_account.id,
    #             'credit': self.settlement_amount,
    #             'date_maturity': fields.Date.today(),
    #             'move_id': account_move.id,
    #             'company_id': self.contract_id.company_id.id,
    #         }
    #         move_lines.append((0, 0, credit_vals))

    #     else:
    #         # Negative settlement amount: Refund to tenant (debit expense, credit tenant)
    #         # Debit: Expense account (500002 - income becomes expense when negative)
    #         debit_account = self.env['account.account'].search([('code', '=', '100011')], limit=1)
    #         if not debit_account:
    #             raise UserError(_("Expense account (500002) not found."))

    #         debit_vals = {
    #             'partner_id': self.contract_id.partner_id.id,
    #             'account_id': debit_account.id,
    #             'debit': abs(self.settlement_amount),  # Use absolute value
    #             'date_maturity': fields.Date.today(),
    #             'move_id': account_move.id,
    #             'company_id': self.contract_id.company_id.id,
    #         }
    #         move_lines.append((0, 0, debit_vals))

    #         # Credit: Accounts Receivable (102011)
    #         credit_account = self.env['account.account'].search([('code', '=', '100012')], limit=1)
    #         if not credit_account:
    #             raise UserError(_("Accounts Receivable account (100012) not found."))

    #         credit_vals = {
    #             'partner_id': self.contract_id.partner_id.id,
    #             'account_id': credit_account.id,
    #             'credit': abs(self.settlement_amount),  # Use absolute value
    #             'date_maturity': fields.Date.today(),
    #             'move_id': account_move.id,
    #             'company_id': self.contract_id.company_id.id,
    #         }
    #         move_lines.append((0, 0, credit_vals))

        
    #     account_move.write({'line_ids': move_lines})

    #     # Return action to show the created journal entry
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Journal Entry',
    #         'res_model': 'account.move',
    #         'res_id': account_move.id,
    #         'view_mode': 'form',
    #         'view_type': 'form',
    #         'target': 'current',
    #     }    
        
        
  
    
    # def create_draft_entry(self):
    #     for rec in self:
    #         if not rec.settlement_amount:
    #             raise UserError(_("Settlement amount is zero. No journal entry required."))

    #         if not rec.journal_id:
    #             raise UserError(_("Please configure a journal on the contract."))

    #         partner = rec.contract_id.partner_id
    #         if not partner:
    #             raise UserError(_("Contract partner not found."))

    #         # Decide accounts
    #         receivable_account = partner.property_account_receivable_id
    #         payable_account = partner.property_account_payable_id

    #         if not receivable_account or not payable_account:
    #             raise UserError(_("Please configure receivable/payable accounts on the partner."))

    #         # Settlement / termination income-expense account
    #         settlement_account = rec.contract_id.company_id.income_currency_exchange_account_id
    #         if not settlement_account:
    #             raise UserError(_("Please configure a Settlement account on the company."))

    #         amount = abs(rec.settlement_amount)

    #         # Determine direction
    #         if rec.settlement_amount > 0:
    #             # Tenant needs to pay
    #             debit_line = {
    #                 'account_id': receivable_account.id,
    #                 'partner_id': partner.id,
    #                 'debit': amount,
    #                 'credit': 0.0,
    #                 'name': _('Contract Termination Settlement'),
    #             }
    #             credit_line = {
    #                 'account_id': settlement_account.id,
    #                 'partner_id': partner.id,
    #                 'debit': 0.0,
    #                 'credit': amount,
    #                 'name': _('Contract Termination Settlement'),
    #             }
    #         else:
    #             # Refund to tenant
    #             debit_line = {
    #                 'account_id': settlement_account.id,
    #                 'partner_id': partner.id,
    #                 'debit': amount,
    #                 'credit': 0.0,
    #                 'name': _('Contract Termination Refund'),
    #             }
    #             credit_line = {
    #                 'account_id': payable_account.id,
    #                 'partner_id': partner.id,
    #                 'debit': 0.0,
    #                 'credit': amount,
    #                 'name': _('Contract Termination Refund'),
    #             }

    #         move_vals = {
    #             'move_type': 'entry',
    #             'journal_id': rec.journal_id.id,
    #             'date': fields.Date.context_today(self),
    #             'ref': rec.name,
    #             'line_ids': [(0, 0, debit_line), (0, 0, credit_line)],
    #         }

    #         move = self.env['account.move'].create(move_vals)
    #         rec.move_id = move.id

    #         # Optional: link move to termination
    #         rec.message_post(
    #             body=_("Draft settlement journal entry created: %s") % move.name
    #         )

    #         return {
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'account.move',
    #             'view_mode': 'form',
    #             'res_id': move.id,
    #         }

    _WIZARD_MOVE_REFS = {
        'security_deposit': 'Security Deposite Return',
        'penalty': 'Penalty Charges on Termination',
        'vat': 'VAT reversation',
    }

    def _wizard_moves_exist(self, contract):
        Move = self.env['account.move']
        return {
            key: bool(Move.search_count([
                ('inv_contract_id', '=', contract.id),
                ('ref', '=', ref),
                ('state', '!=', 'cancel'),
            ], limit=1))
            for key, ref in self._WIZARD_MOVE_REFS.items()
        }

    def _get_termination_accounts(self, contract, partner):
        company = contract.company_id
        return {
            'security_deposit': company.termination_security_deposit_account_id,
            'penalty': company.termination_penalty_income_account_id,
            'deferred': company.termination_deferred_revenue_account_id,
            'revenue': company.termination_revenue_account_id,
            'vat': company.termination_vat_output_account_id,
            'payable': (
                company.termination_payable_account_id
                or partner.property_account_payable_id
            ),
            'receivable': (
                company.termination_receivable_account_id
                or partner.property_account_receivable_id
            ),
        }

    def _get_paid_rent_untaxed(self, contract):
        cashed = contract._get_rent_installment_cheques().filtered(
            lambda c: c.status1 == 'cashed'
        )
        return sum(cashed.mapped('amount'))

    def _get_tax_rate(self, contract):
        tax = contract._get_contract_tax()
        return (tax.amount / 100.0) if tax else 0.0

    def _get_termination_revenue_amount(self):
        """Revenue for the termination month only; prior months are already recognized."""
        self.ensure_one()
        contract = self.contract_id
        currency = contract.contract_currency_id
        termination = self.date_stop
        date_start = self.date_start
        day_value = self.day_value or 0.0
        if not termination or not date_start or not day_value:
            return 0.0
        month_start = termination.replace(day=1)
        revenue_start = max(month_start, date_start)
        if termination < revenue_start:
            return 0.0
        revenue_days = (termination - revenue_start).days + 1
        return currency.round(revenue_days * day_value)

    def _get_termination_amounts(self):
        self.ensure_one()
        contract = self.contract_id
        currency = contract.contract_currency_id

        paid_untaxed = self._get_paid_rent_untaxed(contract)
        revenue_amt = self._get_termination_revenue_amount()
        deferred_amt = currency.round(max(paid_untaxed - revenue_amt, 0.0))

        amounts = {
            'security_deposit': currency.round(self.security_deposit or 0.0),
            'penalty': currency.round(self.penality_amount or 0.0),
            'deferred': deferred_amt,
            'revenue': revenue_amt,
            'vat': 0.0,
        }

        if self.termination_type == 'latetermination' and contract.tax_amount and contract.no_of_days:
            vat_amt = (contract.tax_amount / contract.no_of_days) * abs(self.balance_period or 0)
        elif paid_untaxed and deferred_amt:
            cashed = contract._get_rent_installment_cheques().filtered(
                lambda c: c.status1 == 'cashed'
            )
            paid_tax = sum(cashed.mapped('tax_amount'))
            if paid_tax:
                vat_amt = paid_tax * (deferred_amt / paid_untaxed)
            else:
                tax_rate = self._get_tax_rate(contract)
                vat_amt = deferred_amt * tax_rate if tax_rate else 0.0
        else:
            vat_amt = 0.0
        amounts['vat'] = currency.round(max(vat_amt, 0.0))

        return amounts

    def _prepare_termination_draft_line(self, partner, account, debit, credit, label, analytic_distribution):
        if not account:
            return False
        debit = debit or 0.0
        credit = credit or 0.0
        if not debit and not credit:
            return False
        line_vals = {
            'account_id': account.id,
            'partner_id': partner.id,
            'debit': debit,
            'credit': credit,
            'name': label,
        }
        if analytic_distribution:
            line_vals['analytic_distribution'] = analytic_distribution
        return line_vals

    def _prepare_termination_draft_lines(self):
        self.ensure_one()
        contract = self.contract_id
        partner = contract.partner_id
        currency = contract.contract_currency_id
        accounts = self._get_termination_accounts(contract, partner)
        amounts = self._get_termination_amounts()
        analytic = contract._get_invoice_analytic_distribution()

        lines = []

        def add_line(account_key, debit=0.0, credit=0.0, label=''):
            line = self._prepare_termination_draft_line(
                partner, accounts[account_key], debit, credit, label, analytic,
            )
            if line:
                lines.append(line)

        if amounts['security_deposit']:
            add_line(
                'security_deposit', debit=amounts['security_deposit'],
                label=_('Security Deposit Release'),
            )
        if amounts['penalty']:
            add_line(
                'penalty', credit=amounts['penalty'],
                label=_('Termination Penalty'),
            )
        if amounts['deferred']:
            add_line(
                'deferred', debit=amounts['deferred'],
                label=_('Deferred Revenue Reversal'),
            )
        if amounts['revenue']:
            add_line(
                'revenue', credit=amounts['revenue'],
                label=_('Rent Revenue Recognition'),
            )
        if amounts['vat']:
            add_line(
                'vat', debit=amounts['vat'],
                label=_('VAT Output Adjustment'),
            )

        total_debit = sum(line['debit'] for line in lines)
        total_credit = sum(line['credit'] for line in lines)
        balance = currency.round(total_debit - total_credit)

        if balance > 0:
            add_line(
                'payable', credit=balance,
                label=_('Termination Settlement (Payable)'),
            )
        elif balance < 0:
            add_line(
                'receivable', debit=abs(balance),
                label=_('Termination Settlement (Receivable)'),
            )

        return lines

    def create_draft_entry(self):
        for rec in self:
            if rec.move_id:
                raise UserError(_("A settlement journal entry already exists for this termination."))

            if not rec.journal_id:
                raise UserError(_("Please configure a journal on the contract."))

            partner = rec.contract_id.partner_id
            if not partner:
                raise UserError(_("Contract partner not found."))

            contract = rec.contract_id
            accounts = rec._get_termination_accounts(contract, partner)
            amounts = rec._get_termination_amounts()

            account_checks = [
                ('security_deposit', _('Termination Security Deposit Account'), amounts['security_deposit']),
                ('penalty', _('Termination Penalty Income Account'), amounts['penalty']),
                ('deferred', _('Termination Deferred Revenue Account'), amounts['deferred']),
                ('revenue', _('Termination Revenue Account'), amounts['revenue']),
                ('vat', _('Termination VAT Output Account'), amounts['vat']),
            ]
            missing = [
                label for _key, label, amount in account_checks
                if amount and not accounts[_key]
            ]
            if not accounts['payable']:
                missing.append(_('Termination Payable Account'))
            if not accounts['receivable']:
                missing.append(_('Termination Receivable Account'))
            if missing:
                raise UserError(_(
                    'Please configure the following accounts under Accounting '
                    'Settings > Contract Termination Settlement: %s'
                ) % ', '.join(missing))

            line_vals_list = rec._prepare_termination_draft_lines()
            if not line_vals_list:
                raise UserError(_("No journal lines to create. Check termination amounts."))

            currency = rec.contract_currency_id
            total_debit = currency.round(sum(line['debit'] for line in line_vals_list))
            total_credit = currency.round(sum(line['credit'] for line in line_vals_list))
            if currency.compare_amounts(total_debit, total_credit) != 0:
                raise UserError(_(
                    'Journal entry is unbalanced (Debit: %(debit)s, Credit: %(credit)s).',
                    debit=total_debit,
                    credit=total_credit,
                ))

            move_vals = {
                'move_type': 'entry',
                'journal_id': rec.journal_id.id,
                'date': fields.Date.context_today(self),
                'ref': rec.name,
                'inv_contract_id': contract.id,
                'partner_id': partner.id,
                'line_ids': [(0, 0, line_vals) for line_vals in line_vals_list],
            }

            move = self.env['account.move'].create(move_vals)
            rec.move_id = move.id

            rec.message_post(
                body=_("Draft settlement journal entry created: %s") % move.name
            )

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': move.id,
            }

            
    def format_report_currency(self, amount, currency=None):
        """Format currency for PDF reports (strip unicode chars that break wkhtmltopdf)."""
        self.ensure_one()
        from odoo.tools.misc import format_amount
        currency = currency or self.contract_currency_id or self.company_id.currency_id
        formatted = format_amount(self.env, amount or 0.0, currency)
        formatted = formatted.replace('\u00a0', ' ')
        for char in ('\ufeff', '\u200b', '\u200c', '\u200d', '\u2060'):
            formatted = formatted.replace(char, '')
        return formatted

    def action_print_termination_record(self):
        self.ensure_one()
        return self.env.ref(
            'bliss_property_management.action_contract_termination_report'
        ).report_action(self)

    def action_open_settlement_entry(self):
        self.ensure_one()

        if not self.move_id:
            raise UserError(_("No settlement journal entry found."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Settlement Journal Entry'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
        }



        

    def action_inspection_check(self):
        self.ensure_one()
        return {
            'name': _('Inspection'),
            'type': 'ir.actions.act_window',
            'res_model': 'contract.termination.inspection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_contract_term_id': self.id
            }
        }

        # self.write({'state_term': 'inspection_checked'})
        # self.unit_id.status = "inspection"






    def action_unit_maintenance(self):
        self.write({'state_term': 'maintenance_inprogress'})
        self.unit_id.status = "maintenance"






class ContractTerminationInspectionLine(models.Model):
    _name = 'contract.termination.inspection.line'
    _description = 'Inspection History'

    contract_term_id = fields.Many2one(
        'contract.termination',
        string="Termination",
        ondelete='cascade'
    )

    inspection_date = fields.Datetime(
        string="Inspection Date",
        default=fields.Datetime.now
    )

    paint_condition = fields.Selection([
        ('good', 'Good'),
        ('minor_damage', 'Minor Damage'),
        ('major_damage', 'Major Damage'),
    ])

    door_condition = fields.Selection([
        ('good', 'Good'),
        ('repair_needed', 'Repair Needed'),
        ('replacement_needed', 'Replacement Needed'),
    ])

    # fan_condition = fields.Selection([
    #     ('working', 'Working'),
    #     ('not_working', 'Not Working'),
    # ])

    light_condition = fields.Selection([
        ('working', 'Working'),
        ('not_working', 'Not Working'),
    ])

    # ac_condition = fields.Selection([
    #     ('working', 'Working'),
    #     ('not_working', 'Not Working'),
    #     ('not_applicable', 'Not Applicable'),
    # ])

    appliance_remarks = fields.Text(string="Other Remarks")

    inspection_attachment_ids = fields.Many2many(
        'ir.attachment',
        string="Inspection Photos"
    )

