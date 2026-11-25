
from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_date = fields.Date(string='Payment Date')

    customer_alt_street = fields.Char(string='Street')
    customer_alt_street2 = fields.Char(string='Street 2')
    customer_alt_zip = fields.Char(string='ZIP')
    customer_alt_city = fields.Char(string='City')
    customer_alt_state_id = fields.Many2one( 'res.country.state',string='State',ondelete='restrict',domain="[('country_id', '=?', customer_alt_country_id)]",)
    customer_alt_country_id = fields.Many2one('res.country',string='Country', ondelete='restrict',)
    customer_alt_country_code = fields.Char( related='customer_alt_country_id.code',string='Country Code',)
