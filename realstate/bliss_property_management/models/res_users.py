from odoo import models, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, vals):
        user = super(ResUsers, self).create(vals)
        if user.partner_id:
            user.partner_id.contact_type = 'inter'
        return user