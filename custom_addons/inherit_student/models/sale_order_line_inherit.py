
from odoo import models, fields


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    custom_discount_percentage = fields.Float(
        string='Discount Percentage',
    )
