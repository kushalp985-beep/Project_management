from odoo import models, fields, api


class StudentStandard(models.Model):
    _name = 'student.standard'
    _description = 'Student Standard'

    name = fields.Char(
        string='Standard',
        required=True
    )

    description = fields.Text(
        string='Description'
    )

    subject_ids = fields.Many2many(
    'student.subject',
    'student_standard_subject_rel',
    'standard_id',
    'subject_id',
    string='Subjects'
)


    active = fields.Boolean(
        string='Active',
        default=True
    )

    standard_line_ids = fields.One2many(
    'student.standard.line',
    'standard_id',
    string='Classes'
)


    class_teacher = fields.Many2one(
    'student.teacher',
    string='Class Teacher',
)   
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     
    class_line_ids = fields.One2many(
        'student.standard.line',
        'standard_id',
        string='Classes'
    )
