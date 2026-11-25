from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    maintenance_id = fields.Many2one('maintenance.request')

