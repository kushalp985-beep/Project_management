from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    student_notes = fields.Char(string="Student Notes",config_parameter="inherit_student.student_notes")

    def set_values(self):
        super().set_values()    

        notes = self.student_notes or ''

        students = self.env['student.management'].sudo().search([])
        students.write({
            'notes': notes
        })
