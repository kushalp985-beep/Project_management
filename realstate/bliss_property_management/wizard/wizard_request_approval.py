from odoo import fields, models , _,api


class RequestApproval(models.TransientModel):
   _name = 'request.approval'
   _description = 'Request Approval'
   user_ids = fields.Many2one('res.users', string='Users')
   contract_id = fields.Many2one('property.contract', string='Contract')

   @api.model
   def default_get(self, fields):
      result = super(RequestApproval, self).default_get(fields)
      contract_id = self.env['property.contract'].browse(self._context.get('active_id', False))
      if contract_id:
         result['contract_id'] = contract_id.id
      return result



   def request_approval(self):
      selected_user = self.user_ids
      user_name = selected_user.name if selected_user else "No user selected"
      message_body = _("Approval request sent to %s. ") % user_name
      self.contract_id.message_post(body=message_body, message_type='notification')
      self.contract_id.state = "pwaiting"


      activity_model = self.env['mail.activity']
      activity_type_todo = self.env.ref('mail.mail_activity_data_todo')
      today = fields.Date.today()
      activity_vals = {
         'display_name': _("Request Approval from %s") % user_name,
         'summary': _("Please review and approve %s") % self.contract_id.name,
         'user_id': selected_user.id,
         'res_id': self.contract_id.id,
         'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'property.contract')]).id,
         'activity_type_id': activity_type_todo.id,
         'date_deadline': today,
      }
      new_activity = activity_model.create(activity_vals)
      return {
         'res_model': 'mail.activity',
         'res_id': new_activity.id,
         'name': 'View Activity',
      }


