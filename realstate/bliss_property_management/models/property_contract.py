import base64
import logging
import io

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, float_is_zero
from odoo.tools.misc import format_amount
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta


_logger = logging.getLogger(__name__)


class PropertyContract(models.Model):
    _name = "property.contract"
    _description = "property contract"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string="Name", compute="_compute_name")
    code = fields.Char(string="Code", required=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('Contract.seq.code'))
    attachment_ids = fields.Many2many('ir.attachment', string="Attachments")
    project_id = fields.Many2one('property.project', string='Project', tracking=True)
    unit_id = fields.Many2one('property.unit', string="Unit", required=True)
    owner_id = fields.Many2one(
        'res.partner',
        string='Owner',
        domain=[('contact_type', '=', 'owner')],
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        compute='_compute_accounting_company_id',
        store=True,
        readonly=False,
        help='Managing company used for accounting documents.',
    )

    ejari_fees = fields.Monetary(string="Ejari Fees", currency_field='contract_currency_id')
    
    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Approved'),
        ('blocked', 'Blocked')], string='Kanban State',
        copy=False,  store=True, readonly=False)
    active = fields.Boolean(default=True, string="Active", copy=False)
    partner_id = fields.Many2one('res.partner', string="Tenant", required=True)
    date = fields.Date(default=lambda self: fields.Date.today(), string='Date')
    date_start = fields.Date(string="Start Date", required=True)
    date_stop = fields.Date(string="Stop Date", required=False)
    start_date_from = fields.Date(string="Start From", required=True)
    no_of_days = fields.Integer(string="# of days", compute="_compute_no_of_days")
    day_value = fields.Monetary(string="Day Value", compute="_compute_no_of_days", currency_field='contract_currency_id')
    keys_handover = fields.Date(string="Keys Handover")
    period = fields.Selection([
        ('month', 'Months'),
        ('year', 'Years')], string='Period',
        copy=False, default='month')
    building_id = fields.Many2one('property.building', 'Building Name')
    period_nbr = fields.Integer(string="# of periods", default=1)
    value = fields.Monetary(string="Value",related="unit_id.rent_amount",readonly=False, currency_field='contract_currency_id')
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user)
    notes = fields.Text()
    stage_id = fields.Many2one(
        "property.contract.stage",
        string="Stage",
        tracking=True,
        group_expand="_read_group_stage_ids",
    )

    state = fields.Selection([
        ("proposal", "Proposal"),
        ("pwaiting", "Waiting for approval"),
        ("papproved", "Proposal Approved"),
        ("psent", "Proposal Sent"),
        ("pconfirmed", "Proposal confirmed"),
        ("prejected", "Proposal rejected"),
        ("contract", "New Contract"),
        ("csent", "Contract Sent"),
        ("cconfirmed", "Confirmed"),
        ("clegalapproved", "Legal approved"),
        ("signed", "Signed"),
        ("canceled", "Canceled"),
        ("berenew", "To be renew"),
        ("renewed", "Renewed"),
        ("ctermination", "Termination"),

    ], default='proposal', tracking=True, copy=False, index=True)
    
    
    @api.depends('project_id', 'project_id.managed_by')
    def _compute_accounting_company_id(self):
        for contract in self:
            if contract.project_id and contract.project_id.managed_by:
                contract.company_id = contract.project_id.managed_by
            else:
                contract.company_id = self.env.company

    @api.onchange('project_id')
    def _onchange_project_id(self):
        self.building_id = False
        self.unit_id = False
        if self.project_id:
            self.owner_id = self.project_id.owner_id

    @api.onchange('building_id')
    def _onchange_building_id(self):
        self.unit_id = False
        if self.building_id:
            if self.building_id.project_id:
                self.project_id = self.building_id.project_id
                self.owner_id = self.building_id.project_id.owner_id

    @api.onchange('unit_id')
    def _onchange_unit_id(self):
        if self.unit_id:
            self.building_id = self.unit_id.building_id
            if self.unit_id.project_id:
                self.project_id = self.unit_id.project_id
                self.owner_id = self.unit_id.project_id.owner_id

    @api.onchange('state')
    def _onchange_state_set_stage(self):
        for rec in self:
            if rec.state:
                stage = self.env['property.contract.stage'].search(
                    [('state', '=', rec.state)],
                    limit=1
                )
                if stage:
                    rec.stage_id = stage.id
        
    
    def write(self, vals):
        res = super().write(vals)

        if 'state' in vals:
            state_stage_map = {
                'proposal': 'bliss_property_management.stage_proposal',
                'pwaiting': 'bliss_property_management.stage_waiting',
                'papproved': 'bliss_property_management.stage_papproved',
                'psent': 'bliss_property_management.stage_psent',
                'pconfirmed': 'bliss_property_management.stage_pconfirmed',
                'prejected': 'bliss_property_management.stage_prejected',
                'contract': 'bliss_property_management.stage_contract',
                'csent': 'bliss_property_management.stage_csent',
                'cconfirmed': 'bliss_property_management.stage_cconfirmed',
                'clegalapproved': 'bliss_property_management.stage_legal',
                'signed': 'bliss_property_management.stage_signed',
                'canceled': 'bliss_property_management.stage_canceled',
                'berenew': 'bliss_property_management.stage_berenew',
                'renewed': 'bliss_property_management.stage_renewed',
                'ctermination': 'bliss_property_management.stage_ctermination',
            }

            for record in self:
                xml_id = state_stage_map.get(record.state)
                if xml_id:
                    stage = self.env.ref(xml_id, raise_if_not_found=False)
                    if stage:
                        record.stage_id = stage.id

        return res
    
    
    
    
    
    tax_type = fields.Selection([
        ('included', 'Included'),
        ('excluded', 'Excluded'),
    ], compute='_compute_tax_type', store=True, readonly=True)
    tax_id = fields.Many2one('account.tax', string="VAT")
    discount = fields.Float(string="Discount")
    tax_amount = fields.Monetary(string="Tax Amount", compute="_compute_tax_and_total_value", currency_field='contract_currency_id')
    total_value = fields.Monetary(string="Total Value", compute="_compute_tax_and_total_value", currency_field='contract_currency_id')
    total_paid = fields.Monetary(string="Total Paid", compute="_compute_total_paid_amount", currency_field='contract_currency_id')
    to_be_paid = fields.Monetary(string="To Be Paid", compute="_compute_total_paid_amount", currency_field='contract_currency_id')
    commission_value = fields.Float(string="Commission value %")
    security_deposit = fields.Monetary(string="Security Deposit",currency_field='contract_currency_id')
    security_deposit_check = fields.Boolean(default=True, string="Is Security Deposit Check", copy=False)
    property_type = fields.Selection(
        [
            ('residential', 'Residential'),
            ('commercial', 'Commercial'),
        ],
        related="unit_id.property_type",
        string='Property Type',
        default='commercial',
        required=True,
        readonly=False
    )
    payment_check = fields.Boolean(string="Pay With Checks")
    bank_id = fields.Many2one('res.bank', string="Tenant Bank")
    checks_no = fields.Integer(string="# of Installments")
    journal_id = fields.Many2one('account.journal', string="Payment Journal")
    installment_journal_id = fields.Many2one('account.journal', string="Installment journal")
    first_installment_include_tax = fields.Boolean(string="First Installment Include Tax")
    account_cheque_ids = fields.One2many('account.cheque', 'contract_id', string='Checks')
    can_compute_installments = fields.Boolean(
        compute='_compute_can_compute_installments',
    )
    not_paid_cheque_ids = fields.One2many('account.cheque', 'contract_id',compute="_compute_not_paid_cheque_ids", string='Not Paid Cheque')

    invoice_ids = fields.One2many('account.move', 'inv_contract_id', string='Invoices')
    commission_ids = fields.One2many('account.move', 'contract_id', string='Commission')
    fees_ids = fields.One2many('account.move', 'contract_id', string='Fees')
    checks_count = fields.Integer(string='Checks', compute='_compute_contract_checks_count')
    contract_renewal_count = fields.Integer(string='Contract renewal', compute='_compute_contract_renewal_count')
    contract_term_count = fields.Integer(string='Termination contract ', compute='_compute_contract_term_count')
    invoices_count = fields.Integer(string='Invoices ', compute='_compute_invoice_count')

    media_ids = fields.One2many('property.unit.media', 'contract_id', string='Media')
    has_renewal = fields.Boolean(compute="_compute_has_renewal", string="Has Renewal")
    days_until_end = fields.Integer(string="Days Until End")
    maintenance_billing = fields.Selection(
        related='project_id.maintenance_billing',
        readonly=True,
    )
    maintenance_issue_ids = fields.One2many(
        'maintenance.unit.issue', 'contract_id', string='Maintenance Requests')
    management_fee = fields.Monetary(
        related='unit_id.management_fee',
        string='Management Fee',
        currency_field='contract_currency_id',
        store=True,
        readonly=True,
    )
    management_fee_deducted = fields.Monetary(
        string='Management Fee Collected',
        compute='_compute_total_paid_amount',
        currency_field='contract_currency_id',
    )
    maintenance_charges_deducted = fields.Monetary(
        string='Maintenance Charges Deducted',
        compute='_compute_total_paid_amount',
        currency_field='contract_currency_id',
    )
    maintenance_deducted = fields.Monetary(
        string='Total Maintenance Deducted',
        compute='_compute_total_paid_amount',
        currency_field='contract_currency_id',
    )
    owner_payable = fields.Monetary(
        string='Owner Payable',
        compute='_compute_total_paid_amount',
        currency_field='contract_currency_id',
        help='Rent collected minus maintenance charges.',
    )
    contract_currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_contract_currency_id',
        store=True,
        readonly=True,
    )

    @api.depends('company_id', 'company_id.currency_id', 'project_id.managed_by', 'project_id.managed_by.currency_id')
    def _compute_contract_currency_id(self):
        for contract in self:
            company = contract.company_id
            if not company and contract.project_id and contract.project_id.managed_by:
                company = contract.project_id.managed_by
            contract.contract_currency_id = (
                company.currency_id if company else self.env.company.currency_id
            )
    is_renew = fields.Boolean(string='Is-Renew', compute='_compute_is_renew')
    invoice_payment_term_id = fields.Many2one('account.payment.term',string="Payment Term")
    penalty_amount = fields.Monetary(string="Penalty Amount",currency_field='contract_currency_id')

    @api.depends('account_cheque_ids', 'account_cheque_ids.status1')
    def _compute_can_compute_installments(self):
        for record in self:
            record.can_compute_installments = not record.account_cheque_ids.filtered(
                lambda c: c.status1 != 'cancel'
            )

    @api.depends('account_cheque_ids.status1')
    def _compute_not_paid_cheque_ids(self):
        for record in self:
            record.not_paid_cheque_ids = record.account_cheque_ids.filtered(lambda c: c.status1 not in ('cancel', 'cashed'))

    def _compute_invoice_count(self):
        for contract in self:
            contract.invoices_count = len(contract.invoice_ids)

    def _compute_contract_checks_count(self):
        for contract in self:
            contract.checks_count = self.env['account.cheque'].search_count(
                [('contract_id', '=', contract.id)])

    def _compute_contract_renewal_count(self):
        for contract in self:
            contract.contract_renewal_count = self.env['contract.renewal'].search_count(
                [('contract_id', '=', contract.id)])

    def _compute_contract_term_count(self):
        for contract in self:
            contract.contract_term_count = self.env['contract.termination'].search_count(
                [('contract_id', '=', contract.id)])

    def action_request_approval(self):
        return {
            'name': 'Request Approval',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'request.approval',
            'res_id': False,
            'context': {'active_id': self.id},
            'target': 'new',
        }

    def cancel(self):
        selected_user = self.user_id
        user_name = selected_user.name if selected_user else "No user selected"
        message_body = _("Stage %s has been canceled by %s") % (self.state, user_name)
        self.state = "canceled"
        self.message_post(body=message_body, message_type='notification')
        self.unit_id.state = "available"

    def action_approve_proposal(self):
        self.state = "papproved"
        selected_user = self.env.user
        user_name = selected_user.name if selected_user else "No user selected"
        message_body = _("The proposal has been approved by %s") % (user_name)
        self.message_post(body=message_body, message_type='notification')

    def action_reject_proposal(self):
        return {
            'name': 'Reject Proposal',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'reject.proposal.wizard',
            'res_id': False,
            'context': {'active_id': self.id},
            'target': 'new',
        }

    def action_send_proposal(self):
        mail_template = self.env.ref('bliss_property_management.proposal_email_template')
        ctx = {
            'default_model': self._name,
            'default_res_ids': self.ids,
            'default_template_id': mail_template.id if mail_template else None,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'force_email': True,
            'default_attachment_ids': [(6, 0, [att.id for att in self.attachment_ids])]

        }
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }
        self.state = "psent"
        return action

    def action_confirm_proposal(self):
        self.state = "pconfirmed"
        self.unit_id.state = 'reserved'
        selected_user = self.env.user
        user_name = selected_user.name if selected_user else "No user selected"
        message_body = _("The proposal has been confirmed by %s") % (user_name)
        self.message_post(body=message_body, message_type='notification')

    def action_convert_to_contract(self):
        self.state = "contract"
        selected_user = self.env.user
        user_name = selected_user.name if selected_user else "No user selected"
        message_body = _("The proposal has been converted to a contract by %s") % (user_name)
        self.message_post(body=message_body, message_type='notification')

    def action_send_contract(self):
        mail_template = self.env.ref('bliss_property_management.contract_email_template')
        ctx = {
            'default_model': self._name,
            'default_res_ids': self.ids,
            'default_template_id': mail_template.id if mail_template else None,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'force_email': True,
        }
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }
        self.state = "csent"
        return action

    def action_reset_to_proposal(self):
        self.state = "proposal"
        selected_user = self.env.user
        user_name = selected_user.name if selected_user else "No user selected"
        message_body = _("The proposal has been reset to 'Proposal' state by %s") % (user_name)
        self.message_post(body=message_body, message_type='notification')

    def action_confirm_contract(self):
        self.state = "cconfirmed"
        self.unit_id.state = 'booked'

    def action_legal_approval(self):
        self.state = "clegalapproved"

    def action_fanatical_approval(self):
        for contract in self:
            contract.state = "signed"
            contract.unit_id.state = "rented"
            contract._attach_tenancy_contract_report()

    def action_print_tenancy_contract(self):
        self.ensure_one()
        return self.env.ref(
            'bliss_property_management.action_tenancy_contract_report'
        ).report_action(self)

    def _attach_tenancy_contract_report(self):
        self.ensure_one()
        report = self.env.ref(
            'bliss_property_management.action_tenancy_contract_report',
            raise_if_not_found=False,
        )
        if not report:
            return
        pdf_content, _content_type = self.env['ir.actions.report']._render_qweb_pdf(
            report.report_name,
            res_ids=self.ids,
        )
        attachment = self.env['ir.attachment'].create({
            'name': _('Tenancy Contract - %s.pdf') % (self.code or self.name),
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'property.contract',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        self.message_post(
            body=_('Tenancy contract generated.'),
            attachment_ids=[attachment.id],
        )

    def _get_contract_tax(self):
        """Contract tax or company default sale tax when tax_id is empty."""
        self.ensure_one()
        return self.tax_id or self.company_id.account_sale_tax_id

    def _is_tax_included(self):
        self.ensure_one()
        tax = self._get_contract_tax()
        return bool(tax and tax.price_include)

    @api.depends('tax_id', 'tax_id.price_include', 'company_id', 'company_id.account_sale_tax_id')
    def _compute_tax_type(self):
        for record in self:
            record.tax_type = 'included' if record._is_tax_included() else 'excluded'

    @api.depends(
        'value', 'tax_type', 'tax_id', 'tax_id.price_include',
        'company_id', 'company_id.account_sale_tax_id', 'period', 'period_nbr','ejari_fees'
    )
    def _compute_tax_and_total_value(self):
        for record in self:
            tax = record._get_contract_tax()
            if tax:
                vat_rate = tax.amount
                record.tax_amount = record.value * vat_rate / 100
                if record.tax_type == 'excluded':
                    # Excluded: tax is added on top (e.g. 60000 + 3000 = 63000).
                    record.total_value = record.value + record.tax_amount + record.ejari_fees
                else:
                    # Included: tax is already inside value (e.g. 57000 + 3000 = 60000).
                    record.total_value = record.value + + record.ejari_fees
                record.to_be_paid = record.total_value
            else:
                record.tax_amount = 0.0
                record.total_value = record.value + record.ejari_fees

    @api.onchange('period_nbr')
    def _onchange_period_nbr(self):
        self.value = 0.0
        self.tax_amount = 0.0
        self.total_value = 0.0
        self.total_paid = 0.0
        self.to_be_paid = 0.0

    def _get_installment_dates_from_payment_term(self):
        """Build cheque dates from the selected payment term."""
        self.ensure_one()
        payment_term = self.invoice_payment_term_id
        currency = (
            payment_term.currency_id
            or self.contract_currency_id
            or self.env.company.currency_id
        )
        example_amount = payment_term.example_amount or self.value or 1.0
        terms = payment_term._compute_terms(
            date_ref=self.date_start,
            currency=currency,
            company=self.company_id or self.env.company,
            tax_amount=0,
            tax_amount_currency=0,
            untaxed_amount=example_amount,
            untaxed_amount_currency=example_amount,
            sign=1,
        )
        terms_dates = []
        for info_by_dates in payment_term._get_amount_by_date(terms).values():
            terms_date = info_by_dates['date']
            if isinstance(terms_date, str):
                terms_date = datetime.strptime(terms_date, '%m/%d/%Y').date()
            terms_dates.append(terms_date)
        return terms_dates

    def _get_installment_dates_from_contract(self):
        """Spread installment dates evenly between contract start and end."""
        self.ensure_one()
        if not self.date_start or not self.date_stop:
            raise UserError(_(
                'Please set contract start and end dates, or select a payment term.'
            ))
        days_between = (self.date_stop - self.date_start).days
        if days_between <= 0:
            raise UserError(_('Contract end date must be after the start date.'))
        step_days = days_between // self.checks_no
        return [
            self.date_start + timedelta(days=step_days * i)
            for i in range(self.checks_no)
        ]

    def _get_installment_dates(self):
        self.ensure_one()
        if self.invoice_payment_term_id and self.date_start:
            return self._get_installment_dates_from_payment_term()
        return self._get_installment_dates_from_contract()

    def _get_contract_tax_amount(self):
        self.ensure_one()
        tax = self._get_contract_tax()
        if not tax:
            return 0.0
        return self.value * tax.amount / 100

    def _get_installment_cheque_amounts(self, index, tax_rate):
        """
        Return (amount, tax_amount) for one installment cheque.

        Included example (value=60000, tax=5%):
            amount=57000, tax_amount=3000  => total 60000

        Excluded example (value=60000, tax=5%):
            amount=60000, tax_amount=3000  => total 63000
        """
        self.ensure_one()
        if not tax_rate or self.checks_no <= 0:
            return self.value / self.checks_no, 0.0

        total_tax = self._get_contract_tax_amount()
        tax_per_installment = total_tax / self.checks_no

        if self.tax_type == 'included':
            amount = (self.value - total_tax) / self.checks_no
        else:
            amount = self.value / self.checks_no

        if self.first_installment_include_tax:
            tax_amount = total_tax if index == 0 else 0.0
        else:
            tax_amount = tax_per_installment

        return amount, tax_amount

    def add_installments(self):
        for record in self:
            if record.checks_no <= 0:
                raise UserError(_('Please enter a valid number of installments.'))
            if not record.date_start:
                raise UserError(_('Please set the contract start date.'))

            existing_cheques = record.account_cheque_ids.filtered(
                lambda c: c.status1 != 'cancel'
            )
            if existing_cheques:
                raise UserError(_(
                    'Checks have already been generated for this contract. '
                    'Delete existing checks before computing again.'
                ))

            contract_tax = record._get_contract_tax()
            tax_rate = contract_tax.amount if contract_tax else 0.0
            terms_dates = record._get_installment_dates()
            nbr_days_installment = 0
            if record.date_start and record.date_stop and record.checks_no:
                nbr_days_installment = (
                    (record.date_stop - record.date_start).days // record.checks_no
                )
            currency = record.contract_currency_id or record.company_id.currency_id
            Cheque = self.env['account.cheque'].with_context(
                computing_contract_installments=True,
            )

            for i in range(record.checks_no):
                amount, tax_amount = record._get_installment_cheque_amounts(i, tax_rate)
                if i == 0 and record.ejari_fees:
                    amount = currency.round(amount + record.ejari_fees)
                if i == record.checks_no - 1:
                    collected = sum(
                        record._get_rent_installment_cheques().mapped('total_amount')
                    )
                    remaining = currency.round(record.total_value - collected)
                    amount = currency.round(remaining - tax_amount)
                    if float_compare(amount, 0.0, precision_rounding=currency.rounding) < 0:
                        raise UserError(_(
                            'Cannot generate checks: the remaining contract balance '
                            '(%(remaining)s) is less than the last installment tax '
                            '(%(tax)s).',
                            remaining=format_amount(self.env, remaining, currency),
                            tax=format_amount(self.env, tax_amount, currency),
                        ))
                cheque_date = (
                    terms_dates[i]
                    if i < len(terms_dates)
                    else record.date_start + timedelta(days=nbr_days_installment * i)
                )
                Cheque.create({
                    'contract_id': record.id,
                    'name': f'Installment {i + 1}',
                    'cheque_number': '',
                    'account_cheque_type': 'incoming',
                    'cheque_receive_date': cheque_date,
                    'amount': amount,
                    'tax_amount': tax_amount,
                    'payee_user_id': record.partner_id.id,
                    'cheque_date': cheque_date,
                    'journal_id': record.journal_id.id,
                    'company_id': record.company_id.id,
                })
            if record.security_deposit and record.security_deposit_check:
                first_cheque_date = terms_dates[0] if terms_dates else record.date_start
                company = record.company_id
                # Use Security Deposit specific accounts (fallback to default incoming accounts)
                sd_credit = (
                    company.security_deposit_in_credit_account_id
                    or company.in_credit_account_id
                )
                sd_debit = (
                    company.security_deposit_in_debit_account_id
                    or company.in_debit_account_id
                )
                self.env['account.cheque'].create({
                    'contract_id': record.id,
                    'name': 'Security Deposit',
                    'cheque_number': '',
                    'account_cheque_type': 'incoming',
                    'cheque_receive_date': first_cheque_date,
                    'amount': record.security_deposit,
                    'tax_amount': 0.0,
                    'payee_user_id': record.partner_id.id,
                    'cheque_date': first_cheque_date,
                    'journal_id': record.journal_id.id,
                    'credit_account_id': sd_credit.id,
                    'debit_account_id': sd_debit.id,
                    'company_id': record.company_id.id,
                })
            if record.management_fee > 0 and record.owner_id:
                first_cheque_date = terms_dates[0] if terms_dates else record.date_start
                company = record.company_id
                if not company.maintenance_management_fee_account_id:
                    raise UserError(_(
                        'Please configure Maintenance Management Fee Account in '
                        'Accounting Settings > Maintenance Expense (Separate Billing).'
                    ))
                mf_debit = company.in_debit_account_id
                if not mf_debit:
                    raise UserError(_(
                        'Please configure the cheque debit account in '
                        'Account Cheque Configuration.'
                    ))
                self.env['account.cheque'].create({
                    'contract_id': record.id,
                    'name': 'Management Fee',
                    'cheque_number': '',
                    'account_cheque_type': 'incoming',
                    'cheque_receive_date': first_cheque_date,
                    'amount': record.management_fee,
                    'tax_amount': 0.0,
                    'payee_user_id': record.owner_id.id,
                    'cheque_date': first_cheque_date,
                    'journal_id': record.journal_id.id,
                    'credit_account_id': company.maintenance_management_fee_account_id.id,
                    'debit_account_id': mf_debit.id,
                    'company_id': record.company_id.id,
                })
    
    def _get_invoice_action_xmlid(self):
        self.ensure_one()
        if self.maintenance_billing == 'separate':
            return 'account.action_move_in_invoice_type'
        return 'account.action_move_out_invoice_type'

    def action_view_invoice(self, invoices=False):
        self.ensure_one()
        if not invoices:
            invoices = self.invoice_ids
        action = self.env['ir.actions.actions']._for_xml_id(
            self._get_invoice_action_xmlid()
        )
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [
                    (state, view) for state, view in action['views'] if view != 'form'
                ]
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action['domain'] = [('id', 'in', invoices.ids)]

        if self.maintenance_billing == 'separate':
            context = {'default_move_type': 'in_invoice'}
            if self.owner_id:
                context['default_partner_id'] = self.owner_id.id
        else:
            context = {'default_move_type': 'out_invoice'}
            if self.partner_id:
                context.update({
                    'default_partner_id': self.partner_id.id,
                    'default_partner_shipping_id': self.partner_id.id,
                    'default_invoice_payment_term_id': (
                        self.partner_id.property_payment_term_id.id
                        or self.env['account.move'].default_get(
                            ['invoice_payment_term_id']
                        ).get('invoice_payment_term_id')
                    ),
                })
        context.update({
            'default_invoice_origin': self.name,
            'default_inv_contract_id': self.id,
        })
        action['context'] = context
        return action

    def _get_invoice_analytic_distribution(self):
        self.ensure_one()
        distribution = {}
        for account in (
            self.project_id.analytic_account_id,
            self.building_id.analytic_account_id,
            self.unit_id.analytic_account_id,
        ):
            if account:
                distribution[str(account.id)] = 100
        return distribution or False

    def _prepare_invoice_line_vals(self, line_vals):
        analytic_distribution = self._get_invoice_analytic_distribution()
        if analytic_distribution:
            line_vals['analytic_distribution'] = analytic_distribution
        return line_vals

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

    def format_report_date(self, date_value):
        """Format dates for PDF reports (wkhtmltopdf-safe, no t-field required)."""
        self.ensure_one()
        from datetime import datetime
        from odoo.tools.misc import format_date
        if not date_value:
            return ''
        if isinstance(date_value, datetime):
            date_value = date_value.date()
        return format_date(self.env, date_value)

    def _get_rent_installment_cheques(self):
        """Incoming installment cheques linked to this contract (excludes security deposit)."""
        self.ensure_one()
        return self.account_cheque_ids.filtered(
            lambda c: (
                c.status1 != 'cancel'
                and c.account_cheque_type == 'incoming'
                and c.name
                and c.name.startswith('Installment')
            )
        )

    def _installment_cheque_sort_key(self, cheque):
        if cheque.name and cheque.name.startswith('Installment'):
            number = cheque.name.rsplit(' ', 1)[-1]
            if number.isdigit():
                return (int(number), cheque.id)
        return (999, cheque.cheque_date or fields.Date.today(), cheque.id)

    def _get_installment_sequence_number(self, cheque):
        if cheque.name and cheque.name.startswith('Installment'):
            number = cheque.name.rsplit(' ', 1)[-1]
            if number.isdigit():
                return int(number)
        return 0

    def _get_last_installment_sequence_number(self):
        """Highest installment sequence (planned count or max existing number)."""
        self.ensure_one()
        if self.checks_no:
            return self.checks_no
        numbers = [
            self._get_installment_sequence_number(cheque)
            for cheque in self._get_rent_installment_cheques()
        ]
        numbers = [number for number in numbers if number > 0]
        return max(numbers) if numbers else 0

    def _get_rent_installment_cheques_sorted(self):
        self.ensure_one()
        return self._get_rent_installment_cheques().sorted(
            key=lambda cheque: self._installment_cheque_sort_key(cheque)
        )

    def _get_last_rent_installment_cheque(self):
        self.ensure_one()
        last_sequence = self._get_last_installment_sequence_number()
        if not last_sequence:
            return self.env['account.cheque']
        for cheque in self._get_rent_installment_cheques_sorted():
            if self._get_installment_sequence_number(cheque) == last_sequence:
                return cheque
        return self.env['account.cheque']

    def _is_last_rent_installment_cheque(self, cheque):
        self.ensure_one()
        if cheque not in self._get_rent_installment_cheques():
            return False
        last_sequence = self._get_last_installment_sequence_number()
        return (
            last_sequence > 0
            and self._get_installment_sequence_number(cheque) == last_sequence
        )

    def _get_installment_collection_target(self):
        self.ensure_one()
        return self.total_value

    def _get_installment_collected_total(self, exclude_cheque=None):
        self.ensure_one()
        cheques = self._get_rent_installment_cheques_sorted()
        if exclude_cheque:
            cheques = cheques.filtered(lambda c: c != exclude_cheque)
        return sum(cheques.mapped('total_amount'))

    def _get_remaining_installment_balance(self, exclude_cheque=None):
        self.ensure_one()
        return (
            self._get_installment_collection_target()
            - self._get_installment_collected_total(exclude_cheque=exclude_cheque)
        )

    def _is_first_rent_installment_cheque(self, cheque):
        self.ensure_one()
        if cheque not in self._get_rent_installment_cheques():
            return False
        return self._get_installment_sequence_number(cheque) == 1

    def _get_security_deposit_cheque(self):
        """Return the security deposit cheque (if generated)."""
        self.ensure_one()
        return self.account_cheque_ids.filtered(
            lambda c: (
                c.status1 != 'cancel'
                and c.account_cheque_type == 'incoming'
                and c.name == 'Security Deposit'
            )
        )[:1]

    def _get_management_fee_cheque(self):
        """Return the management fee cheque (if generated)."""
        self.ensure_one()
        return self.account_cheque_ids.filtered(
            lambda c: (
                c.status1 != 'cancel'
                and c.account_cheque_type == 'incoming'
                and c.name == 'Management Fee'
            )
        )


    def _get_security_deposit_invoice_account(self):
        """Account for security deposit invoice lines (from config / cheque)."""
        self.ensure_one()
        sd_cheque = self._get_security_deposit_cheque()
        if sd_cheque and sd_cheque.credit_account_id:
            return sd_cheque.credit_account_id
        account = self.company_id.security_deposit_in_credit_account_id
        if not account:
            raise UserError(_(
                'Please configure Security Deposit accounts in '
                'Security Deposit Configuration settings.'
            ))
        return account

    def _get_ejari_amount_for_cheque(self, cheque):
        """Ejari fee amount included on the first installment cheque only."""
        self.ensure_one()
        if not cheque or not self._is_first_rent_installment_cheque(cheque):
            return 0.0
        return self.ejari_fees or 0.0

    def _prepare_vat_invoice_line_vals(self, cheque):
        """Explicit VAT line when all contract tax is on installment 1."""
        self.ensure_one()
        if (
            not cheque
            or not self.first_installment_include_tax
            or not self._is_first_rent_installment_cheque(cheque)
        ):
            return False
        currency = self.contract_currency_id or self.company_id.currency_id
        if float_is_zero(cheque.tax_amount, precision_rounding=currency.rounding):
            return False
        tax_account = self.company_id.cheque_tax_account_id
        if not tax_account:
            raise UserError(_(
                'Please configure Cheque Tax Account in Account Cheque Configuration.'
            ))
        return self._prepare_tenant_invoice_line_vals(
            _('VAT'),
            cheque.tax_amount,
            account_id=tax_account.id,
            use_product=False,
        )

    def _prepare_ejari_invoice_line_vals(self, cheque):
        """Explicit Ejari fee line on the first installment invoice."""
        self.ensure_one()
        ejari_amount = self._get_ejari_amount_for_cheque(cheque)
        currency = self.contract_currency_id or self.company_id.currency_id
        if float_is_zero(ejari_amount, precision_rounding=currency.rounding):
            return False
        ejari_account = self.company_id.ejari_fee_credit_account_id
        if not ejari_account:
            raise UserError(_(
                'Please configure Ejari Fee Credit Account under Accounting '
                'Settings > Ejari Fee Configuration.'
            ))
        return self._prepare_tenant_invoice_line_vals(
            _('Ejari Fee'),
            ejari_amount,
            account_id=ejari_account.id,
            use_product=False,
        )

    def _prepare_security_deposit_invoice_line_vals(self):
        """Create an invoice line for the security deposit."""
        self.ensure_one()
        if not self.security_deposit_check or not self.security_deposit:
            return False
        sd_cheque = self._get_security_deposit_cheque()
        if sd_cheque and sd_cheque._security_deposit_already_booked_on_cheque():
            return False
        amount = sd_cheque.amount if sd_cheque else self.security_deposit
        return self._prepare_tenant_invoice_line_vals(
            _('Security Deposit'),
            amount,
            tax_ids=[],
            account_id=self._get_security_deposit_invoice_account().id,
            use_product=False,
        )

    def _sync_unit_product_tax(self):
        """Align unit product sale taxes with the contract tax (standard Odoo flow)."""
        self.ensure_one()
        if not self.unit_id.product_id:
            self.unit_id.create_products()
        product = self.unit_id.product_id
        contract_tax = self._get_contract_tax()
        if contract_tax:
            product.taxes_id = [(6, 0, [contract_tax.id])]
        else:
            product.taxes_id = [(5, 0, 0)]

    def _get_tenant_invoice_untaxed_amount(self):
        """Untaxed rent total for a consolidated tenant invoice."""
        self.ensure_one()
        cheques = self._get_rent_installment_cheques()
        if cheques:
            return sum(cheques.mapped('amount'))
        if self._is_tax_included():
            return self.value - self._get_contract_tax_amount()
        return self.value

    def _get_rent_invoice_price_unit(self, cheque=None):
        """Return invoice unit price matching cheque totals and Odoo tax configuration."""
        self.ensure_one()
        if cheque:
            if self.first_installment_include_tax:
                if self._is_first_rent_installment_cheque(cheque):
                    return cheque.amount - self._get_ejari_amount_for_cheque(cheque)
                return cheque.amount
            if self._is_tax_included():
                return cheque.amount + cheque.tax_amount
            return cheque.amount
        price_unit = self._get_tenant_invoice_untaxed_amount()
        if self._is_tax_included():
            cheques = self._get_rent_installment_cheques()
            if cheques:
                return sum(cheques.mapped('amount')) + sum(cheques.mapped('tax_amount'))
            return self.value
        return price_unit

    def _get_contract_duration_months(self):
        """Whole months between contract start and end (inclusive)."""
        self.ensure_one()
        if not self.date_start or not self.date_stop:
            return 0
        delta = relativedelta(self.date_stop + timedelta(days=1), self.date_start)
        return max(delta.years * 12 + delta.months, 0)

    def _get_months_per_installment(self):
        """Months of rent each installment covers (duration / installment count)."""
        self.ensure_one()
        installment_count = self.checks_no or len(self._get_rent_installment_cheques())
        if installment_count <= 0:
            raise UserError(_('Please set the number of installments on the contract.'))
        duration_months = self._get_contract_duration_months()
        if duration_months <= 0:
            raise UserError(_(
                'Please set contract start and end dates before creating '
                'tenant invoices.'
            ))
        return duration_months / installment_count

    def _get_rent_installment_index(self, cheque):
        """Zero-based position of a rent installment cheque on the contract."""
        self.ensure_one()
        cheques = self._get_rent_installment_cheques_sorted()
        for index, installment_cheque in enumerate(cheques):
            if installment_cheque == cheque:
                return index
        return 0

    def _get_rent_deferred_dates(self, cheque=None):
        """Return deferral window for rent recognition.

        Commercial (per cheque): spread each installment over
        (contract duration / number of installments) months from contract
        start, independent of cheque date.
        Residential (consolidated): spread over the full contract period.
        """
        self.ensure_one()
        if not self.date_start or not self.date_stop:
            raise UserError(_(
                'Please set contract start and end dates before creating '
                'tenant invoices.'
            ))
        if not cheque:
            return self.date_start, self.date_stop

        months_per_installment = self._get_months_per_installment()
        installment_index = self._get_rent_installment_index(cheque)

        start_month_offset = int(installment_index * months_per_installment)
        end_month_offset = int((installment_index + 1) * months_per_installment)

        deferred_start = self.date_start + relativedelta(months=start_month_offset)
        deferred_end = self.date_start + relativedelta(months=end_month_offset, days=-1)

        if deferred_start < self.date_start:
            deferred_start = self.date_start
        if deferred_end > self.date_stop:
            deferred_end = self.date_stop
        if deferred_end < deferred_start:
            deferred_end = deferred_start
        return deferred_start, deferred_end

    def _append_rent_invoice_lines(self, invoice_line_ids, cheque=None, rent_line_name=None):
        """Add rent line; taxes come from the unit product (standard Odoo)."""
        self.ensure_one()
        self._sync_unit_product_tax()
        price_unit = self._get_rent_invoice_price_unit(cheque=cheque)
        line_name = rent_line_name or ('Contract :' + self.name)
        invoice_line_ids.append((0, 0, self._prepare_tenant_invoice_line_vals(
            line_name, price_unit, cheque=cheque,
        )))
        if (
            cheque
            and self.first_installment_include_tax
            and self._is_first_rent_installment_cheque(cheque)
        ):
            vat_line = self._prepare_vat_invoice_line_vals(cheque)
            if vat_line:
                invoice_line_ids.append((0, 0, vat_line))
            ejari_line = self._prepare_ejari_invoice_line_vals(cheque)
            if ejari_line:
                invoice_line_ids.append((0, 0, ejari_line))
        return invoice_line_ids

    def _prepare_tenant_invoice_line_vals(
        self, name, price_unit, tax_ids=False, account_id=False,
        use_product=True, cheque=None,
    ):
        self.ensure_one()
        line_vals = {
            'name': name,
            'quantity': 1.0,
            'price_unit': price_unit,
        }
        if use_product:
            if not self.unit_id.product_id:
                self.unit_id.create_products()
            deferred_start, deferred_end = self._get_rent_deferred_dates(cheque=cheque)
            line_vals.update({
                'product_id': self.unit_id.product_id.id,
                'deferred_start_date': deferred_start,
                'deferred_end_date': deferred_end,
            })
        if account_id:
            line_vals['account_id'] = account_id
        if cheque and self.first_installment_include_tax:
            line_vals['tax_ids'] = [(6, 0, [])]
        if not use_product:
            # Security deposit: explicit liability account, no taxes.
            line_vals['is_imported'] = True
            line_vals['tax_ids'] = [(6, 0, [])]
        return self._prepare_invoice_line_vals(line_vals)

    def _prepare_tenant_invoice_vals(self, cheque=None):
        self.ensure_one()
        if cheque:
            invoice_line_ids = []
            self._append_rent_invoice_lines(
                invoice_line_ids,
                cheque=cheque,
                rent_line_name=f'{self.name} - {cheque.name}',
            )
            # Add the security deposit on the first installment invoice (commercial) and on any single invoice (residential).
            if self._is_first_rent_installment_cheque(cheque):
                sd_line = self._prepare_security_deposit_invoice_line_vals()
                if sd_line:
                    invoice_line_ids.append((0, 0, sd_line))
            invoice_date = cheque.cheque_date or self.date
            vals = {
                'partner_id': self.partner_id.id,
                'move_type': 'out_invoice',
                'invoice_date': invoice_date,
                'company_id': self.company_id.id,
                'inv_contract_id': self.id,
                'account_cheque_id': cheque.id,
                'invoice_origin': self.name,
                'invoice_line_ids': invoice_line_ids,
            }
        else:
            invoice_line_ids = []
            self._append_rent_invoice_lines(invoice_line_ids)
            sd_line = self._prepare_security_deposit_invoice_line_vals()
            if sd_line:
                invoice_line_ids.append((0, 0, sd_line))
            vals = {
                'partner_id': self.partner_id.id,
                'move_type': 'out_invoice',
                'invoice_date': self.date,
                'company_id': self.company_id.id,
                'inv_contract_id': self.id,
                'invoice_payment_term_id': self.invoice_payment_term_id.id,
                'invoice_line_ids': invoice_line_ids,
            }
        return vals

    def _prepare_commercial_tenant_invoice_vals_list(self):
        self.ensure_one()
        cheques = self._get_rent_installment_cheques().sorted(
            key=lambda c: (c.cheque_date or fields.Date.today(), c.id)
        )
        if not cheques:
            raise UserError(_(
                'Commercial contracts with check payments require installment '
                'cheques. Generate installments before creating tenant invoices.'
            ))
        # already_invoiced = cheques.filtered(
        #     lambda c: self.env['account.move'].search_count([
        #         ('inv_contract_id', '=', self.id),
        #         ('account_cheque_id', '=', c.id),
        #         ('state', '!=', 'cancel'),
        #     ])
        # )
        # if already_invoiced:
        #     raise UserError(_(
        #         'Tenant invoices already exist for one or more installment '
        #         'cheques on this contract.'
        #     ))
        return [self._prepare_tenant_invoice_vals(cheque=cheque) for cheque in cheques]

    def _get_active_tenant_invoices(self):
        self.ensure_one()
        return self.invoice_ids.filtered(
            lambda m: m.move_type == 'out_invoice' and m.state != 'cancel'
        )

    def _get_active_owner_bills(self):
        self.ensure_one()
        return self.invoice_ids.filtered(
            lambda m: (
                m.move_type == 'in_invoice'
                and m.state != 'cancel'
                and m.partner_id == self.owner_id
            )
        )

    def _get_active_commission_invoices(self):
        self.ensure_one()
        return self.commission_ids.filtered(lambda m: m.state != 'cancel')

    def _check_separate_maintenance_owner_bill_accounts(self):
        self.ensure_one()
        company = self.company_id
        if not company.separate_maintenance_debit_account_id:
            raise UserError(_(
                'Please configure Separate Maintenance Debit Account in '
                'Accounting Settings > Maintenance Expense (Separate Billing).'
            ))
        if not company.separate_maintenance_credit_account_id:
            raise UserError(_(
                'Please configure Separate Maintenance Credit Account in '
                'Accounting Settings > Maintenance Expense (Separate Billing).'
            ))

    def _prepare_owner_vendor_bill_vals(self):
        self.ensure_one()
        if not self.owner_id:
            raise UserError(_('Please set the property owner on this contract.'))
        rent_collected = self.total_paid
        if rent_collected <= 0:
            raise UserError(_(
                'No rent collected yet. Cash tenant cheques before generating the owner bill.'
            ))
        self._check_separate_maintenance_owner_bill_accounts()
        company = self.company_id

        line_vals = [(0, 0, self._prepare_invoice_line_vals({
            'name': _('Total Rent Collected'),
            'quantity': 1.0,
            'price_unit': rent_collected,
            'account_id': company.separate_maintenance_debit_account_id.id,
        }))]
        if self.maintenance_charges_deducted:
            line_vals.append((0, 0, self._prepare_invoice_line_vals({
                'name': _('Maintenance Charges'),
                'quantity': -1.0,
                'price_unit': self.maintenance_charges_deducted,
                'account_id': company.separate_maintenance_credit_account_id.id,
            })))

        return {
            'partner_id': self.owner_id.id,
            'move_type': 'in_invoice',
            'invoice_date': fields.Date.context_today(self),
            'company_id': self.company_id.id,
            'inv_contract_id': self.id,
            'invoice_origin': self.name,
            'invoice_line_ids': line_vals,
        }

    def _check_cheque_tax_account_configured(self):
        self.ensure_one()
        if self._get_contract_tax() and not self.company_id.cheque_tax_account_id:
            raise UserError(_(
                'Please configure Cheque Tax Account in Account Cheque Configuration.'
            ))

    def action_invoice(self):
        self.ensure_one()
        account_move_obj = self.env['account.move']
        if self.maintenance_billing == 'separate':
            if self._get_active_owner_bills():
                raise UserError(_(
                    'An owner bill already exists for this contract. '
                    'Cancel the existing bill before creating a new one.'
                ))
            invoices = account_move_obj.create(self._prepare_owner_vendor_bill_vals())
        elif (
            self.property_type == 'commercial'
            and self._get_rent_installment_cheques()
        ):
            self._check_cheque_tax_account_configured()
            invoices = account_move_obj
            for invoice_vals in self._prepare_commercial_tenant_invoice_vals_list():
                invoices |= account_move_obj.create(invoice_vals)
        else:
            self._check_cheque_tax_account_configured()
            if self._get_active_tenant_invoices():
                raise UserError(_(
                    'A tenant invoice already exists for this contract. '
                    'Cancel the existing invoice before creating a new one.'
                ))
            invoices = account_move_obj.create(self._prepare_tenant_invoice_vals())
        return self.action_view_invoice(invoices)
    
    def compute_commission(self):
        self.ensure_one()
        if not self.commission_value:
            raise UserError(_('Please define a commision value for the contract'))
        if self._get_active_commission_invoices():
            raise UserError(_(
                'A commission invoice already exists for this contract. '
                'Cancel the existing invoice before creating a new one.'
            ))
        commission_line = {
            'name': 'commission for contract :' + self.name,
            'quantity': 1.0,
            'price_unit': self.value / 100 * self.commission_value,
        }
        contract_tax = self._get_contract_tax()
        if contract_tax:
            commission_line['tax_ids'] = [(4, contract_tax.id)]
        self.env['account.move'].create({
            'partner_id': self.unit_id.building_id.project_id.managed_by.partner_id.id,
            'move_type': 'in_invoice',
            'invoice_date': self.date,
            'company_id': self.company_id.id,
            'contract_id': self.id,
            'inv_contract_id': self.id,
            'invoice_line_ids': [(0, 0, self._prepare_invoice_line_vals(commission_line))],
        })

    @api.depends('code')
    def _compute_name(self):
        for record in self:
            record.name = f"contract {record.code}"

    @api.depends('date_start', 'date_stop', 'value')
    def _compute_no_of_days(self):
        for record in self:
            if record.date_start and record.date_stop:
                start_date = fields.Date.from_string(record.date_start)
                stop_date = fields.Date.from_string(record.date_stop)
                duration =  (stop_date - start_date).days
                record.no_of_days = duration
                record.day_value = record.value / duration
            else:
                record.day_value = 0.0
                record.no_of_days = 0

    def action_preview(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/property_contract/preview/%s' % self.id,
            'target': 'new',
        }

    def _get_name_contract_content_view(self):
        """ This method can be inherited by localizations who want to localize the online quotation view. """
        self.ensure_one()
        return 'bliss_property_management.sale_order_portal_content'

    def _compute_access_url(self):
        super()._compute_access_url()
        for contract in self:
            contract.access_url = f'/property_contract/preview/{contract.id}'

    @api.model
    def check_contract_end_dates(self):
        today = fields.Date.today()
        threshold_date = today + timedelta(days=120)

        contracts = self.search([('date_stop', '!=', False)])
        for contract in contracts:
            contract.days_until_end = (contract.date_stop - today).days if contract.date_stop else 0

        contracts = self.search([
            ('date_stop', '<=', threshold_date),
            ('date_stop', '>=', today),
            ('state', '=', 'signed')])

        for contract in contracts:
            contract.write({"state": "berenew"})

            template_id = self.env.ref('bliss_property_management.email_template_contract_report').id
            self.env['mail.template'].browse(template_id).send_mail(contract.id, force_send=True)

            contract.message_post(body=f"End date reminder email sent to {contract.partner_id.email}")


    def action_contract_terminate(self):
        return {
            'name': 'Contract termination',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'contract.termination.wizard',
            'res_id': False,
            'context': {'active_id': self.id},
            'target': 'new',
        }

    def action_renew_contract(self):
        self.ensure_one()
        return {
            'name': 'Contract Renewal',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'contract.renewal',
            'res_id': False,
            'context': {'default_contract_id': self.id},
            'target': 'current',
        }

    def check_contracts_expiring_in_15_days(self):
        today = fields.Date.today()
        target_date = today + timedelta(days=15)
        contracts = self.env['property.contract'].search([('date_stop', '=', target_date)])
        for contract in contracts:
            renewal = self.search([('contract_id', '=', contract.id)])
            if renewal:
                renewal.write({"state_renew": "senttolegel"})
                renewal.message_post(
                    body=f"Contract renewal state changed to 'sent_to_legel'")

    def _compute_has_renewal(self):
        for contract in self:
            renewal_exists = self.env['contract.renewal'].search_count([('contract_id', '=', contract.id)]) > 0
            contract.has_renewal = renewal_exists


    def check_contracts_expiring_in_15_days(self):
        today = fields.Date.today()
        target_date = today + timedelta(days=15)
        contracts = self.env['property.contract'].search([('date_stop', '<=', target_date)])
        for contract in contracts:
            contract.days_until_end = (contract.date_stop - fields.Date.today()).days

    @api.depends(
        'account_cheque_ids',
        'account_cheque_ids.name',
        'account_cheque_ids.status1',
        'account_cheque_ids.amount',
        'account_cheque_ids.tax_amount',
        'total_value',
        'maintenance_billing',
        'maintenance_issue_ids.state',
        'maintenance_issue_ids.price',
    )
    def _compute_total_paid_amount(self):
        for contract in self:
            rent_collected = sum(
                contract._get_rent_installment_cheques().filtered(
                    lambda c: c.status1 == 'cashed'
                ).mapped('total_amount')
            )
            contract.total_paid = rent_collected

            management_fee_collected = sum(
                contract._get_management_fee_cheque().filtered(
                    lambda c: c.status1 == 'cashed'
                ).mapped('amount')
            )
            contract.management_fee_deducted = management_fee_collected

            if contract.maintenance_billing == 'separate':
                done_issues = contract.maintenance_issue_ids.filtered(
                    lambda issue: issue.state == 'done'
                )
                maintenance_charges = sum(done_issues.mapped('price'))
                contract.maintenance_charges_deducted = maintenance_charges
                contract.maintenance_deducted = maintenance_charges
                contract.owner_payable = rent_collected - maintenance_charges
            else:
                contract.maintenance_charges_deducted = 0.0
                contract.maintenance_deducted = 0.0
                contract.owner_payable = 0.0

            contract.to_be_paid = contract.total_value - rent_collected

    @api.depends('contract_renewal_count')
    def _compute_is_renew(self):
        for record in self:
            record.is_renew = record.contract_renewal_count > 0

    def _get_cheque_inquiry_status_label(self, cheque, payment_moves):
        """Human-readable cheque status for the inquiry PDF grid."""
        self.ensure_one()
        currency = self.contract_currency_id or self.company_id.currency_id
        rounding = currency.rounding if currency else 0.01
        paid = sum(payment_moves.mapped('amount_total'))
        if cheque.status1 == 'cashed' and not cheque.is_partial:
            if float_compare(paid, cheque.total_amount, precision_rounding=rounding) >= 0:
                return 'Received'
        if cheque.is_partial or (
            payment_moves
            and float_compare(paid, cheque.total_amount, precision_rounding=rounding) < 0
            and paid > 0
        ):
            return 'Partial'
        if cheque.status1 in ('draft', 'registered', 'deposited'):
            return 'Pending'
        if cheque.status1 == 'cashed':
            return 'Received'
        selection = dict(cheque._fields['status1'].selection)
        return selection.get(cheque.status1, cheque.status1 or '')

    def _get_cheque_inquiry_pending_amount(self, cheque, payment_moves):
        self.ensure_one()
        currency = self.contract_currency_id or self.company_id.currency_id
        rounding = currency.rounding if currency else 0.01
        if cheque.status1 == 'cashed' and not cheque.is_partial:
            paid = sum(payment_moves.mapped('amount_total'))
            if float_compare(paid, cheque.total_amount, precision_rounding=rounding) >= 0:
                return 0.0
        paid = sum(payment_moves.mapped('amount_total'))
        pending = cheque.total_amount - paid
        if float_compare(pending, 0, precision_rounding=rounding) <= 0:
            return 0.0
        return pending

    def _get_cheque_inquiry_bank_name(self, cheque):
        journal = cheque.journal_id
        if journal.bank_id:
            return journal.bank_id.name
        return journal.name or ''

    def _get_inquiry_cheque_payment_lines(self):
        """One dict per payment row; cheque columns rowspan on first row."""
        self.ensure_one()
        Move = self.env['account.move']
        lines = []
        for installment_no, cheque in enumerate(
            self._get_rent_installment_cheques_sorted(), start=1
        ):
            payments = Move.search([
                ('account_cheque_id', '=', cheque.id),
                ('state', '=', 'posted'),
            ], order='date, id')
            status_label = self._get_cheque_inquiry_status_label(cheque, payments)
            pending = self._get_cheque_inquiry_pending_amount(cheque, payments)
            bank_name = self._get_cheque_inquiry_bank_name(cheque)
            payment_rows = []
            for move in payments:
                payment_rows.append({
                    'payment_date': move.date,
                    'received_amount': move.amount_total,
                    'payment_status': 'Received',
                    'receipt_date': cheque.cash_cleared_date or move.date,
                    'receipt_no': move.name,
                })
            if not payment_rows:
                payment_rows.append({
                    'payment_date': False,
                    'received_amount': 0.0,
                    'payment_status': '',
                    'receipt_date': False,
                    'receipt_no': '',
                })
            rowspan = len(payment_rows)
            for index, payment_row in enumerate(payment_rows):
                lines.append({
                    'show_cheque_cols': index == 0,
                    'cheque_rowspan': rowspan if index == 0 else 0,
                    'installment_no': installment_no,
                    'cheque_number': cheque.cheque_number or str(installment_no),
                    'cheque_date': cheque.cheque_date,
                    'cheque_date_display': self.format_report_date(cheque.cheque_date),
                    'cheque_amount': cheque.total_amount,
                    'cheque_amount_display': self.format_report_currency(cheque.total_amount),
                    'bank': bank_name,
                    'cheque_status': status_label,
                    'pending_amount': pending,
                    'pending_amount_display': self.format_report_currency(pending),
                    'payment_date_display': self.format_report_date(
                        payment_row['payment_date']
                    ),
                    'receipt_date_display': self.format_report_date(
                        payment_row['receipt_date']
                    ),
                    'received_amount_display': self.format_report_currency(
                        payment_row['received_amount']
                    ) if payment_row['received_amount'] else '',
                    **payment_row,
                })
        return lines

    def _get_inquiry_payment_history(self):
        self.ensure_one()
        cheque_ids = self.account_cheque_ids.ids
        if not cheque_ids:
            return []
        moves = self.env['account.move'].search([
            ('account_cheque_id', 'in', cheque_ids),
            ('state', '=', 'posted'),
        ], order='date desc, id desc')
        state_labels = dict(self.env['account.move']._fields['state'].selection)
        history = []
        for move in moves:
            history.append({
                'receipt_no': move.name or '',
                'payment_date_display': self.format_report_date(move.date),
                'amount': move.amount_total,
                'amount_display': self.format_report_currency(move.amount_total),
                'journal': move.journal_id.name or '',
                'payment_method': move.journal_id.name or '',
                'reference': move.ref or '',
                'status': state_labels.get(move.state, move.state),
            })
        return history

    def _get_inquiry_timeline_events(self):
        self.ensure_one()
        events = []
        unit = self.unit_id

        def _add(date_value, label, description=''):
            if date_value:
                if hasattr(date_value, 'date'):
                    date_value = date_value.date()
                events.append({
                    'date': date_value,
                    'date_display': self.format_report_date(date_value),
                    'label': label,
                    'description': description,
                })

        if unit:
            _add(unit.create_date, 'Unit Created', unit.name or unit.unit_no or '')
            if unit.owner_id:
                _add(unit.create_date, 'Owner Assigned', unit.owner_id.name)
        _add(self.create_date, 'Contract Created', self.code)
        if self.is_renew:
            _add(self.date_start, 'Contract Renewed', self.code)
        if self.state == 'signed':
            _add(self.date_start, 'Contract Signed', self.code)
        for cheque in self._get_rent_installment_cheques_sorted():
            if cheque.status1 == 'cashed':
                _add(
                    cheque.cash_cleared_date or cheque.cheque_date,
                    'Rent Received',
                    cheque.cheque_number or cheque.name,
                )
        for issue in self.maintenance_issue_ids:
            _add(issue.complaint_date, 'Maintenance', issue.name)
            if issue.completion_date:
                _add(issue.completion_date, 'Maintenance Completed', issue.name)
        if self.date_stop:
            _add(self.date_stop, 'Contract End Date', self.code)
        if self.state == 'ctermination':
            _add(self.date_stop, 'Contract Terminated', self.code)
        if unit and unit.state == 'available' and self.state in ('ctermination', 'renewed', 'canceled'):
            _add(self.date_stop or fields.Date.today(), 'Unit Vacated', unit.name or '')

        events.sort(key=lambda event: event['date'] or fields.Date.from_string('1900-01-01'))
        return events

    def _get_inquiry_documents(self):
        self.ensure_one()
        documents = []
        Attachment = self.env['ir.attachment']

        def _append(doc_type, attachment, date_value=False):
            if not attachment:
                return
            documents.append({
                'doc_type': doc_type,
                'filename': attachment.name or attachment.display_name,
                'date': date_value or attachment.create_date,
                'date_display': self.format_report_date(
                    date_value or attachment.create_date
                ),
            })

        for attachment in self.attachment_ids:
            _append('Contract Document', attachment, self.date)
        tenant = self.partner_id
        if tenant.passport_image:
            passport_att = Attachment.search([
                ('res_model', '=', 'res.partner'),
                ('res_id', '=', tenant.id),
                ('res_field', '=', 'passport_image'),
            ], limit=1)
            _append('Passport', passport_att, tenant.passport_issue_date)
        if tenant.emirateId_image:
            eid_att = Attachment.search([
                ('res_model', '=', 'res.partner'),
                ('res_id', '=', tenant.id),
                ('res_field', '=', 'emirateId_image'),
            ], limit=1)
            _append('Emirates ID', eid_att, tenant.emirateId_issue_date)
        for cheque in self.account_cheque_ids:
            for attachment in cheque.attchment_ids:
                _append('Cheque Attachment', attachment, cheque.cheque_date)
        for issue in self.maintenance_issue_ids:
            for attachment in issue.before_attachment_ids:
                _append('Maintenance (Before)', attachment, issue.complaint_date)
            for attachment in issue.after_attachment_ids:
                _append('Maintenance (After)', attachment, issue.completion_date)
        for model_name, res_id in (
            ('property.unit', self.unit_id.id),
            ('property.building', self.building_id.id),
            ('property.project', self.project_id.id),
        ):
            if not res_id:
                continue
            for attachment in Attachment.search([
                ('res_model', '=', model_name),
                ('res_id', '=', res_id),
            ]):
                _append('Property Attachment', attachment)
        documents.sort(
            key=lambda doc: doc['date'] or fields.Datetime.from_string('1900-01-01 00:00:00')
        )
        return documents

    def _get_inquiry_unit_display_name(self):
        self.ensure_one()
        unit = self.unit_id
        if not unit:
            return self.name or self.code
        parts = []
        if unit.unit_type_id:
            parts.append(unit.unit_type_id.name)
        if unit.unit_no:
            parts.append(unit.unit_no)
        if parts:
            return ' '.join(parts)
        return unit.name or self.code

    def _get_inquiry_owner_details(self):
        self.ensure_one()
        owner = self.owner_id or self.unit_id.owner_id
        if not owner:
            return {}
        units = self.env['property.unit'].search([('owner_id', '=', owner.id)])
        return {
            'partner': owner,
            'name': owner.name,
            'phone': owner.phone  or '',
            'total_units': len(units),
            'occupied': len(units.filtered(lambda unit: unit.state == 'rented')),
            'vacant': len(units.filtered(lambda unit: unit.state == 'available')),
        }

    def _get_inquiry_tenant_details(self, unit=None):
        self.ensure_one()
        tenant = self.partner_id
        domain = [('partner_id', '=', tenant.id)]
        if unit:
            domain.append(('unit_id', '=', unit.id))
        contracts = self.env['property.contract'].search(
            domain,
            order='date_start desc, id desc',
        )
        return {
            'partner': tenant,
            'name': tenant.name,
            'phone': tenant.phone or '',
            'email': tenant.email or '',
            'nationality': tenant.nationality.name if tenant.nationality else '',
            'emirates_id': tenant.emirateId_number or '',
            'passport': tenant.passport_number or '',
            'contracts': contracts,
        }

    def _get_inquiry_financial_summary(self):
        self.ensure_one()
        termination = self.env['contract.termination'].search(
            [('contract_id', '=', self.id)],
            order='id desc',
            limit=1,
        )
        returned_deposit = 0.0
        if termination:
            returned_deposit = termination.security_deposit or 0.0
        return {
            'total_rent': self.total_value,
            'total_received': self.total_paid,
            'total_pending': self.to_be_paid,
            'total_due': self.to_be_paid,
            'outstanding_balance': self.to_be_paid,
            'security_deposit': self.security_deposit,
            'returned_deposit': returned_deposit,
        }

    def _get_inquiry_maintenance_lines(self):
        self.ensure_one()
        state_labels = dict(
            self.env['maintenance.unit.issue']._fields['state'].selection
        )
        lines = []
        for issue in self.maintenance_issue_ids.sorted(
            key=lambda rec: (rec.complaint_date or fields.Date.today(), rec.id),
            reverse=True,
        ):
            lines.append({
                'reference': issue.name,
                'issue_type': issue.issue_type_id.name or '',
                'complaint_date_display': self.format_report_date(issue.complaint_date),
                'completion_date_display': self.format_report_date(issue.completion_date),
                'employee': issue.employee_id.name or '',
                'state': state_labels.get(issue.state, issue.state),
            })
        return lines

    def _get_inquiry_invoice_lines(self):
        self.ensure_one()
        lines = []
        for invoice in self.invoice_ids.sorted(
            key=lambda move: (move.invoice_date or move.date or fields.Date.from_string('1900-01-01')),
            reverse=True,
        ):
            lines.append({
                'number': invoice.name or invoice.ref or '',
                'date_display': self.format_report_date(
                    invoice.invoice_date or invoice.date
                ),
                'amount_display': self.format_report_currency(invoice.amount_total),
                'paid_display': self.format_report_currency(
                    invoice.amount_total - invoice.amount_residual
                ),
                'residual_display': self.format_report_currency(invoice.amount_residual),
                'payment_state': dict(
                    invoice._fields['payment_state'].selection
                ).get(invoice.payment_state, invoice.payment_state),
            })
        return lines

    @api.model
    def _sync_all_contract_tax_types(self):
        """Resync tax_type from effective tax (module install/upgrade)."""
        contracts = self.search([])
        if contracts:
            contracts._compute_tax_type()
