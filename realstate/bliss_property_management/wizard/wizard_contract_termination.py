from odoo import models, fields, api
from datetime import date, datetime
import logging

_logger = logging.getLogger(__name__)

class WizardContractTermination(models.TransientModel):
    _name = 'contract.termination.wizard'
    _description = 'Contract Termination Wizard'

    termination_type = fields.Selection([
        ("normaltermination", "normal termination"),
        ("earlytermination", "Early termination"),
        ("latetermination", "late termination"),
    ])
    termination_date = fields.Date('Termination Date', required=True)

    def _get_fallback_account(self, company, field_name, fallback_xmlid=None, fallback_code=None):
        account = company[field_name]
        if account:
            return account
        if fallback_xmlid:
            account = self.env.ref(fallback_xmlid, raise_if_not_found=False)
            if account:
                return account
        if fallback_code:
            account = self.env['account.account'].search(
                [('code', '=', fallback_code), ('company_ids', 'in', company.id)],
                limit=1,
            )
            if account:
                return account
        return self.env['account.account']

    def action_create_contract_termination(self):
        active_id = self.env.context.get('active_id')
        contract = self.env['property.contract'].browse(active_id)
        contract.write({'state': 'ctermination'})
        draft_invoice_map = {}
        reversal_total = 0.0
        inv_invoice_id = False
        for invoice_id in contract.invoice_ids.filtered(lambda x:x.journal_id.code == 'MISC'):
            if invoice_id.state == 'draft':
                draft_invoice_map[invoice_id.id] = invoice_id.amount_total_signed
                reversal_total += invoice_id.amount_total_signed
                if inv_invoice_id:
                    invoice_id.unlink()
                else:
                    inv_invoice_id = invoice_id
        if inv_invoice_id and reversal_total > 0:
            move_lines = []
            for line in inv_invoice_id.line_ids:
                if line.credit:
                    move_lines.append((1,line.id,{'credit':reversal_total}))
#                        line.credit = reversal_total
                if line.debit:
                    move_lines.append((1,line.id,{'debit':reversal_total}))
            inv_invoice_id.write({'line_ids' : move_lines})
        
        if contract.security_deposit:
            account_move_obj = self.env['account.move']
            bank = self.env['account.journal'].sudo().search([('type','=','bank')],limit=1)
            move_lines = []
            vals = {
                    'partner_id':contract.partner_id.id,
                    'commercial_partner_id':contract.partner_id.id,
                    'date' : fields.Datetime.now(),
                    'journal_id' : bank.id,
                    'company_id' : contract.company_id.id,
                    'ref' : "Security Deposite Return",
                    'inv_contract_id':contract.id,
            }
            account_move = account_move_obj.create(vals)
            debit_account_id = self._get_fallback_account(
                contract.company_id,
                'security_deposit_in_credit_account_id',
                fallback_code='400043'
            )
            
            debit_vals = {
                    'partner_id' : contract.partner_id.id,
                    'account_id' : debit_account_id.id, 
                    'debit' : contract.security_deposit,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : contract.company_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            # Reverse incoming Security Deposit accounts for refund entry
            credit_account_id = (
                contract.company_id.security_deposit_in_debit_account_id
                or bank.default_account_id
                or self._get_fallback_account(
                    contract.company_id,
                    'deposite_account_id',
                    fallback_code='101001'
                )
            )
            credit_vals = {
                    'partner_id' : contract.partner_id.id,
                    'account_id' : credit_account_id.id, 
                    'credit' : contract.security_deposit,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : contract.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
        
        contract.unit_id.status = 'inspection'
        if contract:
            terminationContract = self.env['contract.termination']
            termination = terminationContract.create({
                'contract_id': contract.id,
                'termination_type': self.termination_type,
                'termination_date': self.termination_date,
                'date_stop': self.termination_date,
                'state_term': 'new',
            })
            
            if self.termination_type == 'earlytermination' and contract.penalty_amount:
                account_move_obj = self.env['account.move']
                bank = self.env['account.journal'].sudo().search([('type','=','bank')],limit=1)
                move_lines = []
                vals = {
                        'partner_id':contract.partner_id.id,
                        'commercial_partner_id':contract.partner_id.id,
                        'date' : fields.Datetime.now(),
                        'journal_id' : bank.id,
                        'company_id' : contract.company_id.id,
                        'ref' : "Penalty Charges on Termination",
                        'inv_contract_id':contract.id,
                }
                account_move = account_move_obj.create(vals)
                debit_account_id = self._get_fallback_account(
                    contract.company_id, 'pdc_for_vendor',
                    fallback_xmlid='bliss_property_management.pdc_vendor_account',
                    fallback_code='100012',
                )
                debit_vals = {
                        'partner_id' : contract.partner_id.id,
                        'account_id' : debit_account_id.id, 
                        'debit' : contract.penalty_amount,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'company_id' : contract.company_id.id,
                }
                move_lines.append((0, 0, debit_vals))
                credit_account_id = self._get_fallback_account(
                    contract.company_id, 'pdc_for_customer',
                    fallback_xmlid='bliss_property_management.pdc_cust_account',
                    fallback_code='100011',
                )
                credit_vals = {
                        'partner_id' : contract.partner_id.id,
                        'account_id' : credit_account_id.id, 
                        'credit' : contract.penalty_amount,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'company_id' : contract.company_id.id,
                }
                move_lines.append((0, 0, credit_vals))
                account_move.write({'line_ids' : move_lines})
            if contract.tax_amount and termination.balance_period:
                tax_amount = (contract.tax_amount / termination.no_of_days) * termination.balance_period
                account_move_obj = self.env['account.move']
                bank = self.env['account.journal'].sudo().search([('type','=','bank')],limit=1)
                move_lines = []
                vals = {
                        'partner_id':contract.partner_id.id,
                        'commercial_partner_id':contract.partner_id.id,
                        'date' : fields.Datetime.now(),
                        'journal_id' : bank.id,
                        'company_id' : contract.company_id.id,
                        'ref' : "VAT reversation",
                        'inv_contract_id':contract.id,
                }
                account_move = account_move_obj.create(vals)
                debit_account_id = self._get_fallback_account(
                    contract.company_id, 'pdc_for_vendor',
                    fallback_xmlid='bliss_property_management.pdc_vendor_account',
                    fallback_code='100012',
                )
                debit_vals = {
                        'partner_id' : contract.partner_id.id,
                        'account_id' : debit_account_id.id, 
                        'debit' : tax_amount,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'company_id' : contract.company_id.id,
                }
                move_lines.append((0, 0, debit_vals))
                credit_account_id = self._get_fallback_account(
                    contract.company_id, 'pdc_for_customer',
                    fallback_xmlid='bliss_property_management.pdc_cust_account',
                    fallback_code='100011',
                )
                credit_vals = {
                        'partner_id' : contract.partner_id.id,
                        'account_id' : credit_account_id.id, 
                        'credit' : tax_amount,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'company_id' : contract.company_id.id,
                }
                move_lines.append((0, 0, credit_vals))
                account_move.write({'line_ids' : move_lines})
            
            return {
                'type': 'ir.actions.act_window',
                'name': 'Contract Termination',
                'res_model': 'contract.termination',
                'res_id': termination.id,
                'view_mode': 'form',
                'target': 'current',
            }
