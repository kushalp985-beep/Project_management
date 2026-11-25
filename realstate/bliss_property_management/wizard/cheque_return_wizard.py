from odoo import models, fields
from datetime import datetime

class ChequeReturnWizard(models.TransientModel):
    _name = 'cheque.return.wizard'
    _description = 'Cheque Return Wizard'
    
    cheque_id = fields.Many2one(
        'account.cheque',
        string='Cheque',
        required=True,
        readonly=True
    )
    cheque_return_date = fields.Date(
        string='Cheque Return Date',
        required=True,
        default=fields.Date.context_today
    )
    cheque_return_reason = fields.Selection([('insufficient_funds','Insufficient Funds'),('sign_mismatch','Irregular Signature'),('account_closed','Account Closed'),('stop_payment','Stop Payment'),('other','Other')],string="Cheque Return Reason")


    def action_confirm_return(self):
        self.ensure_one()

        # write values on cheque
        self.cheque_id.write({
            'cheque_return_date': self.cheque_return_date,
            'cheque_return_reason': self.cheque_return_reason,
        })

        # call original method
        self.cheque_id.set_to_return()

        return {'type': 'ir.actions.act_window_close'}
