from odoo import models, fields, api, _

class RejectProposal(models.Model):
    _name = 'reject.proposal.wizard'
    _description = 'Reject Proposal Wizard'

    reason = fields.Text(string='Reason', required=True)

    def action_confirm_rejection(self):
        proposal = self.env['property.contract'].browse(self.env.context.get('active_id',False))
        if proposal:
            proposal.state = 'prejected'
            proposal.message_post(body=_("The proposal has been rejected due to the following reason: %s") % (self.reason),
                message_type='notification')