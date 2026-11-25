# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from ast import literal_eval


class Company(models.Model):
    _inherit = 'res.company'
	
    in_credit_account_id = fields.Many2one('account.account',string="Credit Account")
    in_debit_account_id = fields.Many2one('account.account',string="Debit Account")
    
    out_credit_account_id = fields.Many2one('account.account',string="Credit Account ")
    out_debit_account_id = fields.Many2one('account.account',string="Debit Account ")
    
    deposite_account_id = fields.Many2one('account.account',string="Deposite Account")
    specific_journal_id = fields.Many2one('account.journal',string="Specific Journal")
    cheque_tax_account_id = fields.Many2one('account.account', string="Cheque Tax Account")
    cheque_deferred_debit_account_id = fields.Many2one(
        'account.account', string='Future Cheque Deferred Debit Account',
    )
    cheque_deferred_credit_account_id = fields.Many2one(
        'account.account', string='Future Cheque Deferred Credit Account',
    )
    # Backward-compatibility alias for old settings view arch in database
    cheque_deferred_revenue_account_id = fields.Many2one(
        'account.account',
        string='Future Cheque Deferred Revenue Account',
        related='cheque_deferred_credit_account_id',
        readonly=False,
    )

    # Security Deposit accounts used for the Security Deposit cheque journal entries
    security_deposit_in_credit_account_id = fields.Many2one(
        'account.account', string="Credit Account"
    )
    security_deposit_in_debit_account_id = fields.Many2one(
        'account.account', string="Debit Account"
    )
    # Backward-compatibility aliases for existing DB views until module upgrade
    security_deposit_out_credit_account_id = fields.Many2one(
        'account.account',
        string="Credit Account",
        related='security_deposit_in_debit_account_id',
        readonly=False,
    )
    security_deposit_out_debit_account_id = fields.Many2one(
        'account.account',
         string="Debit Account",
        related='security_deposit_in_credit_account_id',
        readonly=False,
    )

    pdc_for_customer = fields.Many2one('account.account', string="PDC Account for customer")
    pdc_for_vendor = fields.Many2one('account.account', string="PDC Account for Vendor")
    pdc_cheque = fields.Boolean(string="Allow PDC Option")

    termination_security_deposit_account_id = fields.Many2one(
        'account.account', string='Termination Security Deposit Account',
    )
    termination_penalty_income_account_id = fields.Many2one(
        'account.account', string='Termination Penalty Income Account',
    )
    termination_deferred_revenue_account_id = fields.Many2one(
        'account.account', string='Termination Deferred Revenue Account',
    )
    termination_revenue_account_id = fields.Many2one(
        'account.account', string='Termination Revenue Account',
    )
    termination_vat_output_account_id = fields.Many2one(
        'account.account', string='Termination VAT Output Account',
    )
    termination_payable_account_id = fields.Many2one(
        'account.account', string='Termination Payable Account',
    )
    termination_receivable_account_id = fields.Many2one(
        'account.account', string='Termination Receivable Account',
    )

    maintenance_expense_account_id = fields.Many2one(
        'account.account', string='Maintenance Credit Account',
    )
    maintenance_management_fee_account_id = fields.Many2one(
        'account.account', string='Maintenance Management Fee Account',
    )
    maintenance_clearing_account_id = fields.Many2one(
        'account.account', string='Maintenance Debit Account',
    )
    separate_maintenance_debit_account_id = fields.Many2one(
        'account.account', string='Separate Maintenance Debit Account',
    )
    separate_maintenance_credit_account_id = fields.Many2one(
        'account.account', string='Separate Maintenance Credit Account',
    )
    ejari_fee_debit_account_id = fields.Many2one(
        'account.account', string='Ejari Fee Debit Account',
    )
    ejari_fee_credit_account_id = fields.Many2one(
        'account.account', string='Ejari Fee Credit Account',
    )

   

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    in_credit_account_id = fields.Many2one('account.account',string="Credit Account",related="company_id.in_credit_account_id",readonly=False)
    in_debit_account_id = fields.Many2one('account.account',string="Debit Account",related="company_id.in_debit_account_id",readonly=False)
    
    out_credit_account_id = fields.Many2one('account.account',string="Credit Account ",related="company_id.out_credit_account_id",readonly=False)
    out_debit_account_id = fields.Many2one('account.account',string="Debit Account ",related="company_id.out_debit_account_id",readonly=False)

    security_deposit_in_credit_account_id = fields.Many2one(
        'account.account',
        string="Credit Account",
        related="company_id.security_deposit_in_credit_account_id",
        readonly=False,
    )
    security_deposit_in_debit_account_id = fields.Many2one(
        'account.account',
        string="Debit Account",
        related="company_id.security_deposit_in_debit_account_id",
        readonly=False,
    )
    # Backward-compatibility aliases for old settings view arch in database
    security_deposit_out_credit_account_id = fields.Many2one(
        'account.account',
        string="Security Deposit Outgoing Credit Account",
        related="company_id.security_deposit_out_credit_account_id",
        readonly=False,
    )
    security_deposit_out_debit_account_id = fields.Many2one(
        'account.account',
        string="Security Deposit Outgoing Debit Account",
        related="company_id.security_deposit_out_debit_account_id",
        readonly=False,
    )
    deposite_account_id = fields.Many2one('account.account',string="Deposite Account",related="company_id.deposite_account_id",readonly=False)
    specific_journal_id = fields.Many2one('account.journal',string="Specific Journal",related="company_id.specific_journal_id",readonly=False)
    cheque_tax_account_id = fields.Many2one(
        'account.account',
        string="Cheque Tax Account",
        related="company_id.cheque_tax_account_id",
        readonly=False,
    )
    cheque_deferred_debit_account_id = fields.Many2one(
        'account.account',
        string='Future Cheque Deferred Debit Account',
        related='company_id.cheque_deferred_debit_account_id',
        readonly=False,
    )
    cheque_deferred_credit_account_id = fields.Many2one(
        'account.account',
        string='Future Cheque Deferred Credit Account',
        related='company_id.cheque_deferred_credit_account_id',
        readonly=False,
    )
    # Backward-compatibility alias for old settings view arch in database
    cheque_deferred_revenue_account_id = fields.Many2one(
        'account.account',
        string='Future Cheque Deferred Revenue Account',
        related='company_id.cheque_deferred_revenue_account_id',
        readonly=False,
    )

    pdc_for_customer = fields.Many2one('account.account', string="PDC Account For Customer",related="company_id.pdc_for_customer",readonly=False)
    pdc_for_vendor = fields.Many2one('account.account', string="PDC Account For Vendor",related="company_id.pdc_for_vendor",readonly=False)
    pdc_cheque = fields.Boolean(string="Allow PDC Option",related="company_id.pdc_cheque",readonly=False)

    termination_security_deposit_account_id = fields.Many2one(
        'account.account',
        string='Termination Security Deposit Account',
        related='company_id.termination_security_deposit_account_id',
        readonly=False,
    )
    termination_penalty_income_account_id = fields.Many2one(
        'account.account',
        string='Termination Penalty Income Account',
        related='company_id.termination_penalty_income_account_id',
        readonly=False,
    )
    termination_deferred_revenue_account_id = fields.Many2one(
        'account.account',
        string='Termination Deferred Revenue Account',
        related='company_id.termination_deferred_revenue_account_id',
        readonly=False,
    )
    termination_revenue_account_id = fields.Many2one(
        'account.account',
        string='Termination Revenue Account',
        related='company_id.termination_revenue_account_id',
        readonly=False,
    )
    termination_vat_output_account_id = fields.Many2one(
        'account.account',
        string='Termination VAT Output Account',
        related='company_id.termination_vat_output_account_id',
        readonly=False,
    )
    termination_payable_account_id = fields.Many2one(
        'account.account',
        string='Termination Payable Account',
        related='company_id.termination_payable_account_id',
        readonly=False,
    )
    termination_receivable_account_id = fields.Many2one(
        'account.account',
        string='Termination Receivable Account',
        related='company_id.termination_receivable_account_id',
        readonly=False,
    )

    maintenance_expense_account_id = fields.Many2one(
        'account.account',
        string='Maintenance Credit Account',
        related='company_id.maintenance_expense_account_id',
        readonly=False,
    )
    maintenance_management_fee_account_id = fields.Many2one(
        'account.account',
        string='Maintenance Management Fee Account',
        related='company_id.maintenance_management_fee_account_id',
        readonly=False,
    )
    maintenance_clearing_account_id = fields.Many2one(
        'account.account',
        string='Maintenance Debit Account',
        related='company_id.maintenance_clearing_account_id',
        readonly=False,
    )
    separate_maintenance_debit_account_id = fields.Many2one(
        'account.account',
        string='Separate Maintenance Debit Account',
        related='company_id.separate_maintenance_debit_account_id',
        readonly=False,
    )
    separate_maintenance_credit_account_id = fields.Many2one(
        'account.account',
        string='Separate Maintenance Credit Account',
        related='company_id.separate_maintenance_credit_account_id',
        readonly=False,
    )
    ejari_fee_debit_account_id = fields.Many2one(
        'account.account',
        string='Ejari Fee Debit Account',
        related='company_id.ejari_fee_debit_account_id',
        readonly=False,
    )
    ejari_fee_credit_account_id = fields.Many2one(
        'account.account',
        string='Ejari Fee Credit Account',
        related='company_id.ejari_fee_credit_account_id',
        readonly=False,
    )

    custom_setting_field_1 = fields.Char(string="Custom Setting 1")
    custom_setting_field_2 = fields.Char(string="Custom Setting 2")

    
