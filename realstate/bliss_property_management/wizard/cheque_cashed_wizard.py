from odoo import fields, models, _
from odoo.exceptions import UserError


class ChequeCashedWizard(models.TransientModel):
    _name = 'cheque.cashed.wizard'
    _description = 'Cheque Cashed Wizard'

    cheque_id = fields.Many2one(
        'account.cheque',
        string='Cheque',
        required=True,
        readonly=True,
    )
    cashed_in_date = fields.Date(
        string='Cashed in Date',
        required=True,
        default=fields.Date.context_today,
    )

    def action_confirm_cashed(self):
        self.ensure_one()
        cheque = self.cheque_id
        if not cheque.bank_account_id:
            raise UserError(_('Please set Bank Account before clearing the cheque.'))
        cheque.write({'cash_cleared_date': self.cashed_in_date})
        cheque.action_mark_cleared_from_return()
        return {'type': 'ir.actions.act_window_close'}
