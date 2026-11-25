from odoo import models, fields

class MaintenanceType(models.Model):
    _name = 'maintenance.type'
    _description = 'maintenance type'
    _rec_name = 'name'

    name = fields.Char(string='Name',required=True ,store=True)
    vendor_id = fields.Many2many('res.partner',string="Vendors" ,required=True,domain="[('is_vendor','=',True)]")
    auto_asign_vendor = fields.Boolean(string='Auto Asign Vendor')