from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    custom_setting_field_1 = fields.Char(string="Custom Setting 1")
    custom_setting_field_2 = fields.Char(string="Custom Setting 2")