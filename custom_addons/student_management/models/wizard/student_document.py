from odoo import models, fields


class StudentDocument(models.Model):
    _name = 'student.document'
    _description = 'Student Documents'

    student_id = fields.Many2one(
        'student.management',
        string='Student',
        required=True
    )
    document_name = fields.Char(string='Document Name')
    notes = fields.Text(string='Notes')