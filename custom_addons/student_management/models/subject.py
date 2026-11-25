from odoo import models, fields


class Subject(models.Model):
    _name = 'student.subject'
    _description = 'Student Subject'

    name = fields.Char(string='Subject Name', required=True)
    code = fields.Char(string='Subject Code')
    active = fields.Boolean(string='Active', default=True)
    maximum_marks = fields.Integer(string='maximum Marks')
    passing_marks = fields.Integer(string='passing Marks')
    subject_teacher_id = fields.Many2many('student.teacher',string='Subject Teacher')
    subject_type = fields.Selection(
    [
        ('theory', 'Theory'),
        ('practical', 'Practical'),
    ],  
    )

    standard_ids = fields.Many2many(
    'student.standard',
    'student_standard_subject_rel',
    'subject_id',
    'standard_id',
    string='Standards'
)

    class_ids = fields.Many2many(
        'student.standard.line',
        string='Classes'
    )