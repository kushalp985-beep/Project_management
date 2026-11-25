from odoo import models, fields, api

class Student(models.Model):
    _inherit = 'student.management'

    alternate_street = fields.Char(string='Street')
    alternate_street2 = fields.Char(string='Street 2')
    alternate_zip = fields.Char(string='ZIP')
    alternate_city = fields.Char(string='City')
    alternate_state_id = fields.Many2one('res.country.state',string='State',ondelete='restrict',domain="[('country_id', '=?', alternate_country_id)]",)
    alternate_country_id = fields.Many2one('res.country',string='Country',ondelete='restrict',)
    alternate_country_code = fields.Char(related='alternate_country_id.code',string='Country Code',)
         
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'notes' in fields_list:
            res['notes'] = self.env['ir.config_parameter'].sudo().get_param(
            'inherit_student.student_notes', default=''
            )
        return res



    