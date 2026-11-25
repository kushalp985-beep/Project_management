from odoo import models, fields, api, _

class SendProposal(models.Model):
    _name = 'send.proposal.wizard'
    _description = 'Send Proposal Wizard'

    attachment = fields.Json(string="Attachment", required=True)
    filename = fields.Char(string="Filename")

    def action_confirm_send(self):
        active_id = self.env.context.get('active_id')
        if not active_id:
            return
        attachment_obj = self.env['ir.attachment']
        attachment = attachment_obj.create({
            'name': self.filename,
            'datas': self.attachment,
            'res_model': 'property.contract',
            'res_id': active_id,
            'type': 'binary',
        })
        contract = self.env['property.contract'].browse(active_id)
        contract.attachment_ids = [(4, attachment.id)]
        return {'type': 'ir.actions.act_window_close'}