from odoo import api, fields, models, _

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PropertyFacilities(models.Model):
    _name = 'property.facilities'
    _description = 'Property facilities model'

    name = fields.Char(string="Name")
