from odoo import models, fields

class Maintenance(models.Model):
    _name = 'maintenance.vendor'
    _description = 'maintenance Vendor'

    name = fields.Char(string='Name')
    amount = fields.Char(string='Amount')