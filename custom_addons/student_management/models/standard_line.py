from odoo import models, fields


class StudentStandardLine(models.Model):
    _name = 'student.standard.line'
    _description = 'Standard Class Line'
    _rec_name = 'class_name'

    class_name = fields.Char(
        string='Class Name',
        required=True
    )

    standard_id = fields.Many2one(
        'student.standard',
        string='Standard',
        required=True
    )

    teacher_id = fields.Many2one(
        'student.teacher',
        string='Teacher'
    )
