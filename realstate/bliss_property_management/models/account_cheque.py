# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError
import json
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import format_amount
import ast

class AccountCheque(models.Model):
	_name = "account.cheque"
	_description = 'Account Cheque'
	_order = 'id desc'

	sequence = fields.Char(string='Sequence', readonly=True ,copy=True, index=True)
	name = fields.Char(string="Name", required=True)
	bank_account_id = fields.Many2one('account.account','Bank Account',required=True)
	account_cheque_type = fields.Selection([('incoming','Incoming'),('outgoing','Outgoing')],string="Cheque Type")
	cheque_number = fields.Char(string="Cheque Number",required=True)
	re_amount = fields.Float(string="Remaining Amount",compute='_get_outstanding_info',)
	
	amount = fields.Float(string="Amount",required=True)
	tax_amount = fields.Float(string="Tax Amount", default=0.0, readonly=True)
	total_amount = fields.Float(
		string="Total Amount",
		compute='_compute_total_amount',
		store=True,
	)
	display_tax_amount = fields.Float(
		string="Display Tax Amount",
		compute='_compute_display_amounts',
	)
	display_total_amount = fields.Float(
		string="Display Total Amount",
		compute='_compute_display_amounts',
		inverse='_inverse_display_total_amount',
	)
	cheque_date = fields.Date(string="Cheque Date",default=datetime.now().date())
	cheque_given_date = fields.Date(string="Cheque Given Date")
	cheque_receive_date = fields.Date(string="Cheque Receive Date")
	cheque_return_date = fields.Date(string="Cheque Return Date")
	cash_cleared_date = fields.Date(string="Cash Cleared Date", readonly=True, copy=False, tracking=True)
	payee_user_id = fields.Many2one('res.partner',string="Payee",required=True)
	credit_account_id = fields.Many2one('account.account',string="Credit Account")
	debit_account_id = fields.Many2one('account.account',string="Debit Account")
	comment = fields.Text(string="Comment")
	attchment_ids = fields.One2many('ir.attachment','account_cheque_id',string="Attachment")
	status = fields.Selection([('draft','Draft'),('registered','Registered'),('bounced','Bounced'),('return','Returned'),('cashed','Done'),('cancel','Cancel')],string="Status",default="draft",copy=False, tracking=True, index=True)
	
	status1 = fields.Selection([('draft','Draft'),('registered','Registered'),('bounced','Bounced'),('return','Returned'),('deposited','Deposited'),('transfered','Transfered'),('cashed','Done'),('cancel','Cancel')],string="Status ",default="draft",copy=False, tracking=True, index=True)


	journal_id = fields.Many2one('account.journal',string="Journal",required=True)
	company_id = fields.Many2one('res.company',string="Company",required=True)
	journal_items_count =  fields.Integer(compute='_active_journal_items',string="Journal Items") 
	invoice_ids = fields.One2many('account.move','account_cheque_id',string="Invoices",compute="_count_account_invoice")
	attachment_count  =  fields.Integer('Attachments', compute='_get_attachment_count')
	in_count = fields.Boolean('Incoice',compute='_get_in_count')
	is_partial = fields.Boolean(string='Not reconciled')
	contract_id = fields.Many2one('property.contract', string='Contract')
	contract_term_id = fields.Many2one('contract.termination', string='Contract termination')
	cheque_return_reason = fields.Selection([('insufficient_funds','Insufficient Funds'),('sign_mismatch','Irregular Signature'),('account_closed','Account Closed'),('stop_payment','Stop Payment'),('other','Other')],string="Cheque Return Reason")

	@api.depends('amount', 'tax_amount')
	def _compute_total_amount(self):
		for cheque in self:
			cheque.total_amount = cheque.amount + cheque.tax_amount

	@api.depends('amount', 'tax_amount')
	def _compute_display_amounts(self):
		for cheque in self:
			cheque.display_tax_amount = cheque.tax_amount
			cheque.display_total_amount = cheque.amount + cheque.tax_amount

	def _inverse_display_total_amount(self):
		for cheque in self:
			if cheque.display_total_amount < cheque.tax_amount:
				raise ValidationError(_(
					'Cheque total cannot be less than the tax amount (%(tax)s).',
					tax=cheque.tax_amount,
				))
			cheque.amount = cheque.display_total_amount - cheque.tax_amount

	def _is_contract_installment_cheque(self):
		self.ensure_one()
		return (
			self.account_cheque_type == 'incoming'
			and self.contract_id
			and self.name
			and self.name.startswith('Installment')
			and self.status1 != 'cancel'
		)

	@api.constrains(
		'amount', 'tax_amount', 'display_total_amount', 'contract_id',
		'name', 'account_cheque_type', 'status1',
	)
	def _check_last_installment_balance(self):
		if self.env.context.get('computing_contract_installments'):
			return
		for cheque in self.filtered(lambda c: c._is_contract_installment_cheque()):
			contract = cheque.contract_id
			if not contract._is_last_rent_installment_cheque(cheque):
				continue
			remaining = contract._get_remaining_installment_balance(exclude_cheque=cheque)
			currency = contract.contract_currency_id or contract.company_id.currency_id
			cheque_total = cheque.amount + cheque.tax_amount
			if float_compare(
				cheque_total,
				remaining,
				precision_rounding=currency.rounding,
			) != 0:
				raise ValidationError(_(
					'Last cheque amount must be equal to remaining contract '
					'balance (%(amount)s).',
					amount=format_amount(self.env, remaining, currency),
				))

	def _valid_field_parameter(self, field, name):
		# EXTENDS models
		return name == 'tracking' or super()._valid_field_parameter(field, name)

	
	@api.model 
	def default_get(self, flds): 
		result = super(AccountCheque, self).default_get(flds)
		res = self.env.user.company_id
		user_company_id = self.env.user.company_id

		bank_account = self.env['account.account'].search(
				[('code', '=', '101001')],
				limit=1
			)

		result.update({
			'bank_account_id': bank_account.id,
		})

		if self.env.context.get('default_account_cheque_type') == 'incoming':
			result['credit_account_id'] = user_company_id.in_credit_account_id.id
			result['debit_account_id'] = user_company_id.in_debit_account_id.id
			result['journal_id'] = user_company_id.specific_journal_id.id
			result['company_id'] = user_company_id.id
		else:
			result['credit_account_id'] = user_company_id.out_credit_account_id.id
			result['debit_account_id'] = user_company_id.out_debit_account_id.id
			result['journal_id'] = user_company_id.specific_journal_id.id 
			result['company_id'] = user_company_id.id
		return result 
		
	
	def open_payment_matching_screen(self):

		# Open reconciliation view for customers/suppliers
		move_line_id = False
		account_move_line_ids = self.env['account.move.line'].search([('partner_id', '=', self.payee_user_id.id)])
		for move_line in account_move_line_ids:
			if move_line.account_id.reconcile:
				move_line_id = move_line.id
				break

		action_values = self.env['ir.actions.act_window']._for_xml_id('account_accountant.action_move_line_posted_unreconciled')
		action_context = {'company_ids': [self.company_id.id], 'partner_ids': [self.payee_user_id.id]}

		if self.account_cheque_type == 'incoming':
			action_context.update({'mode': 'customers'})
		elif self.account_cheque_type == 'outgoing':
			action_context.update({'mode': 'suppliers'})

		if account_move_line_ids:
			context = ast.literal_eval(action_values['context'])
			context.update({'search_default_partner_id': self.payee_user_id.id})
			action_values['context'] = context

		return action_values

	def _get_in_count(self):
		for cheque in self:
			cheque.in_count = False
			reference = (
				f"{cheque.sequence}- {cheque.cheque_number}- Registered"
				if cheque.sequence
				else f"{cheque.cheque_number}- Registered"
			)
			if cheque.account_cheque_type == 'incoming' and cheque.credit_account_id:
				credit_lines = self.env['account.move.line'].search([
					('move_id.account_cheque_id', '=', cheque.id),
					('ref', '=', reference),
					('account_id', '=', cheque.credit_account_id.id),
					('reconciled', '=', True),
				], limit=1)
				if credit_lines:
					cheque.status1 = 'cashed'
			elif cheque.account_cheque_type == 'outgoing' and cheque.debit_account_id:
				debit_lines = self.env['account.move.line'].search([
					('move_id.account_cheque_id', '=', cheque.id),
					('ref', '=', reference),
					('account_id', '=', cheque.debit_account_id.id),
					('reconciled', '=', True),
				], limit=1)
				if debit_lines:
					cheque.status = 'cashed'
			cheque.is_partial = cheque.total_amount != cheque.re_amount



	def _get_outstanding_info(self):

		for record in self:
			if record.account_cheque_type == 'incoming' :
				if record.status1 in ('return','deposited','transfered','cashed','bounced'):
					record.re_amount = 0.0
				else:
					record.re_amount = record.total_amount
			if record.account_cheque_type == 'outgoing': 
				if record.status in ('return','transfered','cashed','bounced'):
					record.re_amount = 0.0
				else:
					record.re_amount = record.total_amount
			for move in record.payee_user_id.invoice_ids:
				move.invoice_outstanding_credits_debits_widget = json.dumps(False)
				move.invoice_has_outstanding = False

				if move.state != 'posted' \
						or move.payment_state not in ('not_paid', 'partial') \
						or not move.is_invoice(include_receipts=True):
					continue

				pay_term_lines = move.line_ids\
					.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))

				domain = [
					('account_id', 'in', pay_term_lines.account_id.ids),
					('move_id.state', '=', 'posted'),('move_id.account_cheque_id','=',record.id),
					('partner_id', '=', move.commercial_partner_id.id),
					('reconciled', '=', False),
					'|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
				]

				payments_widget_vals = {'outstanding': True, 'content': [], 'move_id': move.id}

				if move.is_inbound():
					domain.append(('balance', '<', 0.0))
					payments_widget_vals['title'] = _('Outstanding credits')
				else:
					domain.append(('balance', '>', 0.0))
					payments_widget_vals['title'] = _('Outstanding debits')

				for lines in self.env['account.move.line'].search(domain):

					if record.account_cheque_type == 'incoming' :
						if record.status1 not in ('return','deposited','transfered','cashed','bounced'):

							for line in lines:
								# get the outstanding residual value in invoice currency
								if line.currency_id and line.currency_id == move.currency_id:
									amount_to_show = abs(line.amount_residual_currency)
								else:
									currency = line.company_id.currency_id
									amount_to_show = currency._convert(abs(line.amount_residual), move.currency_id, move.company_id,
																	   line.date or fields.Date.today())
									
								if float_is_zero(amount_to_show, precision_rounding=move.currency_id.rounding):
									continue
								record.re_amount = amount_to_show
					if record.account_cheque_type == 'outgoing' :
						if record.status not in ('return','transfered','cashed','bounced'):
							for line in lines:
								# get the outstanding residual value in invoice currency
								if line.currency_id and line.currency_id == move.currency_id:
									amount_to_show = abs(line.amount_residual_currency)
								else:
									currency = line.company_id.currency_id
									amount_to_show = currency._convert(abs(line.amount_residual), move.currency_id, move.company_id,
																	   line.date or fields.Date.today())
									
								if float_is_zero(amount_to_show, precision_rounding=move.currency_id.rounding):
									continue
								record.re_amount = amount_to_show
		
	def _count_account_invoice(self):
		for cheque in self:
			invoice_list = []
			for invoice in cheque.payee_user_id.invoice_ids:
				if invoice.state != 'cancel' and invoice.payment_state != 'paid':
					if cheque.account_cheque_type == 'incoming' and invoice.move_type == 'out_invoice':
						invoice_list.append(invoice.id)
					if cheque.account_cheque_type == 'outgoing' and invoice.move_type == 'in_invoice':
						invoice_list.append(invoice.id)

				if invoice.has_reconciled_entries:
					if cheque.account_cheque_type == 'incoming' and cheque.status1 == 'cancel':
						invoice.button_cancel()
					if cheque.account_cheque_type == 'outgoing' and cheque.status == 'cancel':
						invoice.button_cancel()
			cheque.invoice_ids = [(6, 0, invoice_list)] if invoice_list else None
		return
		
	def _active_journal_items(self):
		for journal_items in self:
			journal_item_ids = self.env['account.move'].search([('account_cheque_id', '=', journal_items.id)])
			journal_items.journal_items_count = sum(len(move.line_ids) for move in journal_item_ids)
		return
		
	def action_view_jornal_items(self):
		self.ensure_one()
		list_of_move_line = []
		for journal_items in self:
			journal_item_ids = self.env['account.move'].search([('account_cheque_id','=',journal_items.id)])
		for move in journal_item_ids:
			for line in move.line_ids:
				list_of_move_line.append(line.id)
		return {
			'name': 'Journal Items',
			'type': 'ir.actions.act_window',
			'view_mode': 'list,form',
			'res_model': 'account.move.line',
			'domain': [('id', 'in' , list_of_move_line)],
		}
		
	def _get_attachment_count(self):
		for cheque in self:
			attachment_ids = self.env['ir.attachment'].search([('account_cheque_id','=',cheque.id)])
			cheque.attachment_count = len(attachment_ids)
		
	def attachment_on_account_cheque(self):
		self.ensure_one()
		return {
			'name': 'Attachment.Details',
			'type': 'ir.actions.act_window',
			'view_mode': 'list,form',
			'res_model': 'ir.attachment',
			'domain': [('account_cheque_id', '=', self.id)],
		}

	def _security_deposit_already_booked_on_cheque(self):
		"""True if this SD cheque already credited the liability account on clearance."""
		self.ensure_one()
		if self.name != 'Security Deposit' or not self.credit_account_id:
			return False
		return bool(self.env['account.move.line'].search([
			('move_id.account_cheque_id', '=', self.id),
			('move_id.state', '=', 'posted'),
			('account_id', '=', self.credit_account_id.id),
			('credit', '>', 0),
		], limit=1))

	def _is_rent_installment_cheque(self):
		self.ensure_one()
		return bool(
			self.name
			and self.name.startswith('Installment')
		)

	def _is_management_fee_cheque(self):
		self.ensure_one()
		return self.name == 'Management Fee'

	def _get_posted_tenant_invoices(self):
		"""Return posted tenant invoices already booking this cheque amount."""
		self.ensure_one()
		if self._is_management_fee_cheque():
			return self.env['account.move']
		Move = self.env['account.move']
		invoices = Move.search([
			('account_cheque_id', '=', self.id),
			('move_type', '=', 'out_invoice'),
			('state', '=', 'posted'),
		])
		if invoices:
			return invoices
		if self._is_rent_installment_cheque() and self.contract_id:
			return Move.search([
				('inv_contract_id', '=', self.contract_id.id),
				('move_type', '=', 'out_invoice'),
				('state', '=', 'posted'),
			]).filtered(
				lambda move: move.invoice_line_ids.filtered(
					lambda line: (
						line.display_type == 'product'
						and self.name in (line.name or '')
					)
				)
			)
		if self.name == 'Security Deposit' and self.contract_id:
			sd_account = self.contract_id._get_security_deposit_invoice_account()
			return Move.search([
				('inv_contract_id', '=', self.contract_id.id),
				('move_type', '=', 'out_invoice'),
				('state', '=', 'posted'),
			]).filtered(
				lambda move: move.invoice_line_ids.filtered(
					lambda line: (
						line.display_type == 'product'
						and (
							line.account_id == sd_account
							or 'security deposit' in (line.name or '').lower()
						)
					)
				)
			)
		return Move

	def _has_posted_tenant_invoice(self):
		self.ensure_one()
		return bool(self._get_posted_tenant_invoices())

	def _get_partner_receivable_account(self):
		self.ensure_one()
		account = self.payee_user_id.with_company(
			self.company_id
		).property_account_receivable_id
		if not account:
			raise UserError(_(
				'Please configure a receivable account for %s.',
				self.payee_user_id.display_name,
			))
		return account

	def _get_draft_tenant_invoices(self):
		"""Draft tenant invoices linked to this cheque or installment."""
		self.ensure_one()
		if self._is_management_fee_cheque():
			return self.env['account.move']
		Move = self.env['account.move']
		invoices = Move.search([
			('account_cheque_id', '=', self.id),
			('move_type', '=', 'out_invoice'),
			('state', '=', 'draft'),
		])
		if invoices:
			return invoices
		if self._is_rent_installment_cheque() and self.contract_id:
			return Move.search([
				('inv_contract_id', '=', self.contract_id.id),
				('move_type', '=', 'out_invoice'),
				('state', '=', 'draft'),
			]).filtered(
				lambda move: move.invoice_line_ids.filtered(
					lambda line: (
						line.display_type == 'product'
						and self.name in (line.name or '')
					)
				)
			)
		return Move

	def _get_deferred_park_amount(self):
		"""Rent amount parked in deferred revenue (excludes VAT and Ejari)."""
		self.ensure_one()
		ejari = 0.0
		if self.contract_id:
			ejari = self.contract_id._get_ejari_amount_for_cheque(self)
		return (self.amount or 0.0) - ejari

	def _get_clearance_split_amounts(self):
		"""Split a rent installment cheque into rent, VAT, and Ejari."""
		self.ensure_one()
		contract = self.contract_id
		ejari = contract._get_ejari_amount_for_cheque(self) if contract else 0.0
		vat = self.tax_amount or 0.0
		rent = (self.amount or 0.0) - ejari
		return {'rent': rent, 'vat': vat, 'ejari': ejari}

	def _should_split_installment_clearance(self):
		"""Use split credits (deferred + VAT + Ejari) instead of in_credit_account."""
		self.ensure_one()
		return bool(
			self.account_cheque_type == 'incoming'
			and self._is_rent_installment_cheque()
			and not self._is_management_fee_cheque()
			and self.contract_id
			and self.company_id.cheque_deferred_credit_account_id
			and not self._has_posted_tenant_invoice()
		)

	def _prepare_incoming_clearance_credit_lines(self, account_move, clear_amount):
		"""Return credit line vals for incoming cheque clearance."""
		self.ensure_one()
		line_defaults = {
			'partner_id': self.payee_user_id.id,
			'date_maturity': datetime.now().date(),
			'move_id': account_move.id,
			'company_id': self.company_id.id,
		}

		if self._has_posted_tenant_invoice():
			return [{
				**line_defaults,
				'account_id': self._get_partner_receivable_account().id,
				'credit': clear_amount,
			}]

		if self._should_split_installment_clearance():
			contract = self.contract_id
			currency = contract.contract_currency_id or self.company_id.currency_id
			rounding = currency.rounding if currency else 0.01
			amounts = self._get_clearance_split_amounts()
			rent_credit = currency.round(amounts['rent'])
			vat_credit = currency.round(amounts['vat'])
			ejari_credit = currency.round(amounts['ejari'])
			parts_total = rent_credit + vat_credit + ejari_credit
			if float_compare(parts_total, clear_amount, precision_rounding=rounding) != 0:
				rent_credit = currency.round(clear_amount - vat_credit - ejari_credit)

			deferred_account = self._get_cheque_deferred_credit_account()
			credit_lines = []
			if not float_is_zero(rent_credit, precision_rounding=rounding):
				credit_lines.append(self._apply_cheque_analytic_distribution({
					**line_defaults,
					'account_id': deferred_account.id,
					'credit': rent_credit,
					'name': _('Deferred Revenue'),
				}))
			if not float_is_zero(vat_credit, precision_rounding=rounding):
				tax_account = contract.company_id.cheque_tax_account_id
				if not tax_account:
					raise UserError(_(
						'Please configure Cheque Tax Account in Account Cheque Configuration.'
					))
				credit_lines.append({
					**line_defaults,
					'account_id': tax_account.id,
					'credit': vat_credit,
					'name': _('VAT'),
				})
			if not float_is_zero(ejari_credit, precision_rounding=rounding):
				ejari_account = contract.company_id.ejari_fee_credit_account_id
				if not ejari_account:
					raise UserError(_(
						'Please configure Ejari Fee Credit Account under Accounting '
						'Settings > Ejari Fee Configuration.'
					))
				credit_lines.append({
					**line_defaults,
					'account_id': ejari_account.id,
					'credit': ejari_credit,
					'name': _('Ejari Fee'),
				})
			if not credit_lines:
				raise UserError(_('No clearance credit lines could be generated for this cheque.'))
			return credit_lines

		if not self.credit_account_id:
			raise UserError(_('Please configure the cheque credit account.'))
		return [{
			**line_defaults,
			'account_id': self.credit_account_id.id,
			'credit': clear_amount,
		}]

	def _prepare_incoming_clearance_credit_vals(self, account_move, clear_amount):
		"""Backward-compatible single-line helper."""
		self.ensure_one()
		lines = self._prepare_incoming_clearance_credit_lines(account_move, clear_amount)
		return lines[0]

	def _reconcile_clearance_with_invoices(self, payment_move):
		self.ensure_one()
		invoices = self._get_posted_tenant_invoices()
		if not invoices:
			return
		payment_lines = payment_move.line_ids.filtered(
			lambda line: (
				line.account_id.account_type == 'asset_receivable'
				and not line.reconciled
			)
		)
		invoice_lines = invoices.line_ids.filtered(
			lambda line: (
				line.account_id.account_type == 'asset_receivable'
				and not line.reconciled
			)
		)
		if payment_lines and invoice_lines:
			(payment_lines + invoice_lines).reconcile()

	def _is_future_rent_installment_cheque(self):
		self.ensure_one()
		return (
			self.account_cheque_type == 'incoming'
			and self._is_rent_installment_cheque()
			and not self._is_management_fee_cheque()
			and self.cheque_date
			and self.cheque_date > fields.Date.today()
		)

	def _should_create_deferred_submit_entry(self):
		self.ensure_one()
		return (
			self._is_future_rent_installment_cheque()
			and not self._has_posted_tenant_invoice()
		)

	def _get_submit_registered_move(self):
		self.ensure_one()
		return self.env['account.move'].search([
			('account_cheque_id', '=', self.id),
			('state', '!=', 'cancel'),
			('ref', 'ilike', 'Registered'),
		], limit=1)

	def _uses_deferred_submit_clearance(self):
		self.ensure_one()
		return bool(self._get_submit_registered_move())

	def _get_cheque_deferred_debit_account(self):
		self.ensure_one()
		account = self.company_id.cheque_deferred_debit_account_id
		if not account:
			raise UserError(_(
				'Please configure Future Cheque Deferred Debit Account in '
				'Accounting Settings > Future Cheque Deferred (Submit / Clear).'
			))
		return account

	def _get_cheque_deferred_credit_account(self):
		self.ensure_one()
		account = self.company_id.cheque_deferred_credit_account_id
		if not account:
			raise UserError(_(
				'Please configure Future Cheque Deferred Credit Account in '
				'Accounting Settings > Future Cheque Deferred (Submit / Clear).'
			))
		return account

	def _apply_cheque_analytic_distribution(self, line_vals):
		self.ensure_one()
		if not self.contract_id:
			return line_vals
		distribution = self.contract_id._get_invoice_analytic_distribution()
		if distribution:
			line_vals['analytic_distribution'] = distribution
		return line_vals

	def _prepare_submit_move_lines(self, account_move):
		self.ensure_one()
		pdc_account = self._get_cheque_deferred_debit_account()
		deferred_account = self._get_cheque_deferred_credit_account()
		park_amount = self._get_deferred_park_amount()
		line_defaults = {
			'partner_id': self.payee_user_id.id,
			'date_maturity': datetime.now().date(),
			'move_id': account_move.id,
			'company_id': self.company_id.id,
		}
		move_lines = []
		move_lines.append((0, 0, self._apply_cheque_analytic_distribution({
			**line_defaults,
			'account_id': pdc_account.id,
			'debit': park_amount,
			'credit': 0.0,
			'name': _('PDC Receivable'),
		})))
		move_lines.append((0, 0, self._apply_cheque_analytic_distribution({
			**line_defaults,
			'account_id': deferred_account.id,
			'debit': 0.0,
			'credit': park_amount,
			'name': _('Deferred Revenue'),
		})))
		return move_lines

	def _create_and_post_submit_move(self):
		self.ensure_one()
		if self._get_submit_registered_move():
			raise UserError(_(
				'A registered journal entry already exists for this cheque.'
			))
		account_move = self.env['account.move'].create({
			'partner_id': self.payee_user_id.id,
			'commercial_partner_id': self.payee_user_id.id,
			'date': self.cheque_receive_date or fields.Date.today(),
			'journal_id': self.journal_id.id,
			'company_id': self.company_id.id,
			'ref': self.cheque_number + '- ' + 'Registered',
			'account_cheque_id': self.id,
			'inv_contract_id': self.contract_id.id if self.contract_id else False,
		})
		move_lines = self._prepare_submit_move_lines(account_move)
		account_move.write({'line_ids': move_lines})
		account_move._post(soft=False)
		return account_move

	def set_to_submit(self):
		"""Register cheque; future rent installments park in deferred revenue."""
		self.ensure_one()
		if self.account_cheque_type == 'incoming' and self.status1 not in ('draft',):
			raise UserError(_('This cheque is already submitted.'))
		if self.account_cheque_type == 'outgoing' and self.status not in ('draft',):
			raise UserError(_('This cheque is already submitted.'))
		if not self.amount:
			raise UserError(_('Please Enter Amount Of Cheque'))

		if self._should_create_deferred_submit_entry():
			self._create_and_post_submit_move()

		if self.account_cheque_type == 'incoming':
			self.status1 = 'registered'
		else:
			self.status = 'registered'
		return True

	def set_to_bounced(self):
		for journal_items in self:
			journal_item_ids = self.env['account.move'].search([('account_cheque_id','=',journal_items.id)])
			journal_item_ids.button_cancel()

		account_move_obj = self.env['account.move']
		move_lines = []
		if self.re_amount:
			if self.account_cheque_type == 'incoming':
				vals = {
						'date' : self.cheque_receive_date,
						'journal_id' : self.journal_id.id,
						'company_id' : self.company_id.id,
						'state' : 'draft',
						'ref' : self.cheque_number + '- ' + 'Bounced',
						'account_cheque_id' : self.id
				}
				account_move = account_move_obj.create(vals)
				debit_vals = {
						'partner_id' : self.payee_user_id.id,
						'account_id' : self.credit_account_id.id, 
						'debit' : self.re_amount,
						'date_maturity' : datetime.now().date(),
						'move_id' : account_move.id,
						'company_id' : self.company_id.id,
				}
				move_lines.append((0, 0, debit_vals))
				credit_vals = {
						'partner_id' : self.payee_user_id.id,
						'account_id' : self.payee_user_id.property_account_receivable_id.id, 
						'credit' : self.re_amount,
						'date_maturity' : datetime.now().date(),
						'move_id' : account_move.id,
						'company_id' : self.company_id.id,
				}
				move_lines.append((0, 0, credit_vals))
				account_move.write({'line_ids' : move_lines})
				account_move.button_cancel()
				self.status1 = 'bounced'
			else:
				vals = {
						'date' : self.cheque_given_date,
						'journal_id' : self.journal_id.id,
						'company_id' : self.company_id.id,
						'state' : 'draft',
						'ref' : self.cheque_number + '- ' + 'Bounced',
						'account_cheque_id' : self.id
				}
				account_move = account_move_obj.create(vals)
				debit_vals = {
						'partner_id' : self.payee_user_id.id,
						'account_id' : self.payee_user_id.property_account_payable_id.id, 
						'debit' : self.re_amount,
						'date_maturity' : datetime.now().date(),
						'move_id' : account_move.id,
						'company_id' : self.company_id.id,
				}
				move_lines.append((0, 0, debit_vals))
				credit_vals = {
						'partner_id' : self.payee_user_id.id,
						'account_id' : self.debit_account_id.id, 
						'credit' : self.re_amount,
						'date_maturity' : datetime.now().date(),
						'move_id' : account_move.id,
						'company_id' : self.company_id.id,
				}
				move_lines.append((0, 0, credit_vals))
				account_move.write({'line_ids' : move_lines})
				account_move.button_cancel()
				self.status = 'bounced'
			return account_move      

	def set_to_return(self):
		
		for journal_items in self:
			journal_item_ids = self.env['account.move'].search([('account_cheque_id','=',journal_items.id)])
			journal_item_ids.button_cancel()

		account_move_obj = self.env['account.move']
		move_lines = []
		list_of_move_line = [] 
		if self.re_amount:

			for journal_items in self:
				journal_item_ids = self.env['account.move'].search([('account_cheque_id','=',journal_items.id)])
			
			matching_dict = []
			for move in journal_item_ids:
				for line in move.line_ids:
					if line.full_reconcile_id:
						matching_dict.append(line)
										
			if len(matching_dict) != 0:
				rec_id = matching_dict[0].full_reconcile_id.id
				a = self.env['account.move.line'].search([('full_reconcile_id','=',rec_id)])
				
				for move_line in a:
					move_line.remove_move_reconcile()
			
			if self.account_cheque_type == 'incoming':
				vals = {
						'date' : self.cheque_receive_date,
						'journal_id' : self.journal_id.id,
						'company_id' : self.company_id.id,
						'state' : 'draft',
						'ref' : self.cheque_number + '- ' + 'Returned',
						'account_cheque_id' : self.id
				}
				account_move = account_move_obj.create(vals)
				debit_vals = {
						'partner_id' : self.payee_user_id.id,
						'account_id' : self.credit_account_id.id, 
						'debit' : self.re_amount,
						'date_maturity' : datetime.now().date(),
						'move_id' : account_move.id,
						'company_id' : self.company_id.id,
				}
				move_lines.append((0, 0, debit_vals))
				credit_vals = {
						'partner_id' : self.payee_user_id.id,
						'account_id' : self.debit_account_id.id, 
						'credit' : self.re_amount,
						'date_maturity' : datetime.now().date(),
						'move_id' : account_move.id,
						'company_id' : self.company_id.id,
				}
				move_lines.append((0, 0, credit_vals))
				account_move.write({'line_ids' : move_lines})
				account_move.button_cancel()
				self.status1 = 'return'
				self.cheque_return_date = datetime.now().date()
			else:
				vals = {
						'date' : self.cheque_given_date,
						'journal_id' : self.journal_id.id,
						'company_id' : self.company_id.id,
						'state' : 'draft',
						'ref' : self.cheque_number + '- ' + 'Returned',
						'account_cheque_id' : self.id
				}
				account_move = account_move_obj.create(vals)
				debit_vals = {
						'partner_id' : self.payee_user_id.id,
						'account_id' : self.credit_account_id.id, 
						'debit' : self.re_amount,
						'date_maturity' : datetime.now().date(),
						'move_id' : account_move.id,
						'company_id' : self.company_id.id,
				}
				move_lines.append((0, 0, debit_vals))
				credit_vals = {
						'partner_id' : self.payee_user_id.id,
						'account_id' : self.debit_account_id.id, 
						'credit' : self.re_amount,
						'date_maturity' : datetime.now().date(),
						'move_id' : account_move.id,
						'company_id' : self.company_id.id,
				}
				move_lines.append((0, 0, credit_vals))
				account_move.write({'line_ids' : move_lines})
				account_move.button_cancel()
				self.status = 'return'
				self.cheque_return_date = datetime.now().date()
				self.write({'cheque_return_date': self.cheque_return_date})
			return account_move           



				  

	def set_to_deposite(self):
		# Deposit step is bypassed. Use "Cleared" directly.
		raise UserError(_('Deposit step is disabled. Please use Cleared directly.'))
				
	def set_to_cancel(self): 
		for journal_items in self:
			journal_item_ids = self.env['account.move'].search([('account_cheque_id','=',journal_items.id)])
			journal_item_ids.button_cancel()

		if self.account_cheque_type == 'incoming':   
			self.status1 = 'cancel' 
		else:
			self.status = 'cancel'

	def action_reset_to_draft(self):
		for cheque in self:
			current_status = (
				cheque.status1
				if cheque.account_cheque_type == 'incoming'
				else cheque.status
			)
			if current_status not in ('cancel', 'cashed'):
				raise UserError(_(
					'Only canceled or done cheques can be reset to draft.'
				))

			moves = self.env['account.move'].search([
				('account_cheque_id', '=', cheque.id),
				('state', '!=', 'cancel'),
			])
			for move in moves:
				reconciled_lines = move.line_ids.filtered('reconciled')
				if reconciled_lines:
					reconciled_lines.remove_move_reconcile()
				if move.state == 'posted':
					move.button_draft()
				move.button_cancel()

			if cheque.account_cheque_type == 'incoming':
				cheque.status1 = 'draft'
			else:
				cheque.status = 'draft'
		return True

	def _get_clearance_amount(self):
		"""Amount to use for clearance JE; returned cheques have re_amount=0 by design."""
		self.ensure_one()
		total_amount = self.amount + self.tax_amount
		if self.account_cheque_type == 'incoming' and self.status1 == 'return':
			return total_amount
		if self.account_cheque_type == 'outgoing' and self.status == 'return':
			return total_amount
		return self.re_amount or total_amount

	def action_mark_cleared(self):
		for cheque in self:
			cheque._validate_clearance(allow_from_return=False)
			cheque._post_clearance(cheque.cheque_date or fields.Date.today())
		return True

	def action_mark_cleared_from_return(self):
		self.ensure_one()
		self._validate_clearance(allow_from_return=True)
		if self.account_cheque_type == 'incoming' and self.status1 != 'return':
			raise UserError(_('Only returned cheques can be cashed from this action.'))
		if self.account_cheque_type == 'outgoing' and self.status != 'return':
			raise UserError(_('Only returned cheques can be cashed from this action.'))
		clear_date = self.cash_cleared_date or fields.Date.today()
		self._post_clearance(clear_date)
		return True

	def _validate_clearance(self, allow_from_return=False):
		self.ensure_one()
		if self.account_cheque_type == 'incoming':
			if self.status1 in ('cashed', 'cancel'):
				raise UserError(_('This cheque is already cleared or canceled.'))
			allowed = ('registered', 'return') if allow_from_return else ('registered',)
			if self.status1 not in allowed:
				raise UserError(_('Please submit the cheque before clearing it.'))
		else:
			if self.status in ('cashed', 'cancel'):
				raise UserError(_('This cheque is already cleared or canceled.'))
			allowed = ('registered', 'return') if allow_from_return else ('registered',)
			if self.status not in allowed:
				raise UserError(_('Please submit the cheque before clearing it.'))

		existing_cashed = self.env['account.move'].search([
			('account_cheque_id', '=', self.id),
			('state', '!=', 'cancel'),
			('ref', 'ilike', 'Cashed'),
		], limit=1)
		if existing_cashed:
			raise UserError(_(
				'A cleared journal entry already exists for this cheque (%s).'
			) % existing_cashed.name)

		if not self._get_clearance_amount():
			raise UserError(_('No remaining amount to clear on this cheque.'))
		if not self.bank_account_id:
			raise UserError(_('Please set Bank Account before clearing the cheque.'))
		if self._get_draft_tenant_invoices() and self._is_rent_installment_cheque():
			raise UserError(_(
				'Please post the tenant invoice for %s before clearing this cheque.',
				self.display_name,
			))

	def _post_clearance(self, clear_date):
		self.ensure_one()
		account_move_obj = self.env['account.move']
		move_lines = []
		if self.account_cheque_type == 'incoming':
			clear_amount = self._get_clearance_amount()
			vals = {
				'date': clear_date,
				'journal_id': self.journal_id.id,
				'company_id': self.company_id.id,
				'partner_id': self.payee_user_id.id,
				'state': 'draft',
				'ref': self.cheque_number + '- ' + 'Cashed',
				'account_cheque_id': self.id,
			}
			if self.contract_id:
				vals['inv_contract_id'] = self.contract_id.id
			account_move = account_move_obj.create(vals)
			debit_vals = {
				'partner_id': self.payee_user_id.id,
				'account_id': self.bank_account_id.id,
				'debit': clear_amount,
				'date_maturity': datetime.now().date(),
				'move_id': account_move.id,
				'company_id': self.company_id.id,
			}
			move_lines.append((0, 0, debit_vals))
			clearance_line_defaults = {
				'partner_id': self.payee_user_id.id,
				'date_maturity': datetime.now().date(),
				'move_id': account_move.id,
				'company_id': self.company_id.id,
			}
			if self._uses_deferred_submit_clearance():
				pdc_account = self._get_cheque_deferred_debit_account()
				contract = self.contract_id
				currency = (
					contract.contract_currency_id
					if contract
					else self.company_id.currency_id
				)
				rounding = currency.rounding if currency else 0.01
				amounts = self._get_clearance_split_amounts()
				pdc_clear = currency.round(amounts['rent'])
				vat_clear = currency.round(amounts['vat'])
				ejari_clear = currency.round(amounts['ejari'])
				move_lines.append((0, 0, self._apply_cheque_analytic_distribution({
					**clearance_line_defaults,
					'account_id': pdc_account.id,
					'credit': pdc_clear,
					'name': _('PDC Receivable Clearance'),
				})))
				if not float_is_zero(vat_clear, precision_rounding=rounding):
					tax_account = contract.company_id.cheque_tax_account_id
					if not tax_account:
						raise UserError(_(
							'Please configure Cheque Tax Account in Account Cheque Configuration.'
						))
					move_lines.append((0, 0, {
						**clearance_line_defaults,
						'account_id': tax_account.id,
						'credit': vat_clear,
						'name': _('VAT'),
					}))
				if not float_is_zero(ejari_clear, precision_rounding=rounding):
					ejari_account = contract.company_id.ejari_fee_credit_account_id
					if not ejari_account:
						raise UserError(_(
							'Please configure Ejari Fee Credit Account under Accounting '
							'Settings > Ejari Fee Configuration.'
						))
					move_lines.append((0, 0, {
						**clearance_line_defaults,
						'account_id': ejari_account.id,
						'credit': ejari_clear,
						'name': _('Ejari Fee'),
					}))
			else:
				for credit_vals in self._prepare_incoming_clearance_credit_lines(
					account_move, clear_amount,
				):
					move_lines.append((0, 0, credit_vals))
			account_move.write({'line_ids': move_lines})
			account_move._post(soft=False)
			if not self._uses_deferred_submit_clearance():
				self._reconcile_clearance_with_invoices(account_move)
			self.status1 = 'cashed'
		else:
			clear_amount = self._get_clearance_amount()
			vals = {
				'date': clear_date,
				'journal_id': self.journal_id.id,
				'company_id': self.company_id.id,
				'state': 'draft',
				'ref': self.cheque_number + '- ' + 'Cashed',
				'account_cheque_id': self.id,
			}
			account_move = account_move_obj.create(vals)
			debit_vals = {
				'partner_id': self.payee_user_id.id,
				'account_id': self.debit_account_id.id,
				'debit': clear_amount,
				'date_maturity': datetime.now().date(),
				'move_id': account_move.id,
				'company_id': self.company_id.id,
			}
			move_lines.append((0, 0, debit_vals))
			credit_vals = {
				'partner_id': self.payee_user_id.id,
				'account_id': self.bank_account_id.id,
				'credit': clear_amount,
				'date_maturity': datetime.now().date(),
				'move_id': account_move.id,
				'company_id': self.company_id.id,
			}
			move_lines.append((0, 0, credit_vals))
			account_move.write({'line_ids': move_lines})
			account_move._post(soft=False)
			self.status = 'cashed'

class ChequeWizard(models.TransientModel):
	_name = 'cheque.wizard'
	_description = 'Cheque Wizard'

	@api.model 
	def default_get(self, flds): 
		result = super(ChequeWizard, self).default_get(flds)
		account_cheque_id = self.env['account.cheque'].browse(self.env.context.get('active_id'))
		if account_cheque_id.account_cheque_type == 'outgoing':
			result['is_outgoing'] = True
		return result
		
	def create_cheque_entry(self):
		account_cheque = self.env['account.cheque'].browse(self.env.context.get('active_ids'))
		account_move_obj = self.env['account.move']
		move_lines = []
		if account_cheque.re_amount:
			if account_cheque.account_cheque_type == 'incoming':
				vals = {
						'date' : self.chequed_date,
						'journal_id' : self.cash_journal_id.id,
						'company_id' : account_cheque.company_id.id,
						'state' : 'draft',
						'ref' : account_cheque.cheque_number + '- ' + 'Cashed',
						'account_cheque_id' : account_cheque.id
				}
				account_move = account_move_obj.create(vals)
				debit_vals = {
						'partner_id' : account_cheque.payee_user_id.id,
						'account_id' : account_cheque.debit_account_id.id, 
						'debit' : account_cheque.re_amount,
						'date_maturity' : datetime.now().date(),
						'move_id' : account_move.id,
						'company_id' : account_cheque.company_id.id,
				}
				move_lines.append((0, 0, debit_vals))
				credit_vals = {
						'partner_id' : account_cheque.payee_user_id.id,
						'account_id' : account_cheque.bank_account_id.id, 
						'credit' : account_cheque.re_amount,
						'date_maturity' : datetime.now().date(),
						'move_id' : account_move.id,
						'company_id' : account_cheque.company_id.id,
				}
				move_lines.append((0, 0, credit_vals))
				account_move.write({'line_ids' : move_lines})
				account_move._post(soft=False)
				account_cheque.status1 = 'cashed'
			else:
				vals = {
						'date' : self.chequed_date,
						'journal_id' : self.cash_journal_id.id,
						'company_id' : account_cheque.company_id.id,
						'state' : 'draft',
						'ref' : account_cheque.cheque_number + '- ' + 'Cashed',
						'account_cheque_id' : account_cheque.id
				}
				account_move = account_move_obj.create(vals)
				debit_vals = {
						'partner_id' : account_cheque.payee_user_id.id,
						'account_id' : account_cheque.credit_account_id.id, 
						'debit' : account_cheque.re_amount,
						'date_maturity' : datetime.now().date(),
						'move_id' : account_move.id,
						'company_id' : account_cheque.company_id.id,
				}
				move_lines.append((0, 0, debit_vals))
				credit_vals = {
						'partner_id' : account_cheque.payee_user_id.id,
						'account_id' : self.bank_account_id.id, 
						'credit' : account_cheque.re_amount,
						'date_maturity' : datetime.now().date(),
						'move_id' : account_move.id,
						'company_id' : account_cheque.company_id.id,
				}
				move_lines.append((0, 0, credit_vals))
				account_move.write({'line_ids' : move_lines})
				account_move._post(soft=False)
				account_cheque.status = 'cashed'
			return account_move

	cash_journal_id = fields.Many2one('account.journal',string="Cash Journal",required=True,domain=[('type', '=', 'cash')])
	chequed_date = fields.Date(string="Cheque Date")
	bank_account_id = fields.Many2one('account.account',string="Bank Account")
	is_outgoing = fields.Boolean(string="Is Outgoing",default=False)
	
class ChequeTransferedWizard(models.TransientModel):
	_name = 'cheque.transfered.wizard'
	_description = 'Cheque Transfered Wizard'

	def create_ckeck_transfer_entry(self):
		account_cheque = self.env['account.cheque'].browse(self.env.context.get('active_ids'))
		account_move_obj = self.env['account.move']
		move_lines = []
		for journal_items in account_cheque:
			journal_item_ids = self.env['account.move'].search([('account_cheque_id','=',journal_items.id)])
			journal_item_ids.button_cancel()

		if account_cheque.re_amount:
			if account_cheque.account_cheque_type == 'incoming':
				vals = {
						'date' : self.transfered_date,
						'journal_id' : account_cheque.journal_id.id,
						'company_id' : account_cheque.company_id.id,
						'state' : 'draft',
						'ref' : account_cheque.cheque_number + '- ' + 'Transfered',
						'account_cheque_id' : account_cheque.id
				}
				account_move = account_move_obj.create(vals)
				debit_vals = {
						'partner_id' : self.contact_id.id,
						'account_id' : account_cheque.credit_account_id.id, 
						'debit' : account_cheque.re_amount,
						'date_maturity' : datetime.now().date(),
						'move_id' : account_move.id,
						'company_id' : account_cheque.company_id.id,
				}
				move_lines.append((0, 0, debit_vals))
				credit_vals = {
						'partner_id' : self.contact_id.id,
						'account_id' : account_cheque.debit_account_id.id, 
						'credit' : account_cheque.re_amount,
						'date_maturity' : datetime.now().date(),
						'move_id' : account_move.id,
						'company_id' : account_cheque.company_id.id,
				}
				move_lines.append((0, 0, credit_vals))
				account_move.write({'line_ids' : move_lines})
				account_cheque.status1 = 'transfered'
				account_cheque.payee_user_id = self.contact_id.id
				return account_move
		
	transfered_date = fields.Date(string="Transfered Date")
	contact_id = fields.Many2one('res.partner',string="Contact")
	
class AccountMoveLine(models.Model):
	_inherit='account.move'

	account_cheque_id  =  fields.Many2one('account.cheque', 'Journal Item')


class ReportWizard(models.TransientModel):
	_name = "report.wizard"
	_description = 'Report Wizard'

	from_date = fields.Date('From Date', required = True)
	to_date = fields.Date('To Date',required = True)
	cheque_type = fields.Selection([('incoming','Incoming'),('outgoing','Outgoing')],string="Cheque Type",default='incoming')
	
	
	def submit(self):
		inc_temp = []
		out_temp = []
		temp = [] 
		
		if self.cheque_type == 'incoming':
			in_account_cheque_ids = self.env['account.cheque'].search([(str('cheque_date'),'>=',self.from_date),(str('cheque_date'),'<=',self.to_date),('account_cheque_type','=','incoming')])
		
			if not in_account_cheque_ids:
				raise UserError(_('There Is No Any Cheque Details.'))
			else:
				for inc in in_account_cheque_ids:
					temp.append(inc.id)
			
		if self.cheque_type == 'outgoing':
			out_account_cheque_ids = self.env['account.cheque'].search([(str('cheque_date'),'>=',self.from_date),(str('cheque_date'),'<=',self.to_date),('account_cheque_type','=','outgoing')])
			
			if not out_account_cheque_ids:
				raise UserError(_('There Is No Any Cheque Details.'))
			else:
				for out in out_account_cheque_ids:
					temp.append(out.id)
							   
		data = temp
		in_data = inc_temp
		out_data = out_temp
		datas = {
			'ids': self._ids,
			'model': 'account.cheque',
			'form': data,
			'from_date':self.from_date,
			'to_date':self.to_date,
			'cheque_type' : self.cheque_type,
		}
		return self.env.ref('bliss_property_management.account_cheque_report_id').report_action(self,data=datas)

class IrAttachment(models.Model):
	_inherit='ir.attachment'

	account_cheque_id  =  fields.Many2one('account.cheque', 'Attchments')
	
