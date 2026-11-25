from odoo import api, models, fields


class res_city(models.Model):
    _inherit = 'res.city'

    country_id = fields.Many2one(
        'res.country',
        string='Country',
        default=lambda self: self.env.ref('base.ae').id,
        required=True,
        readonly=True
    )
