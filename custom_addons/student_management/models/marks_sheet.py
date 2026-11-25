from odoo import models, fields, api


class MarksSheet(models.Model):
    _name = 'student.marks.sheet'
    _description = 'Student Marks Sheet'

    student_id = fields.Many2one(
        'student.management',
        string='Student',
        required=True
    )

    standard = fields.Char(string='Standard')
    academic_year = fields.Char(string='Academic Year')
    exam = fields.Char(string='Exam')
    exam_date = fields.Date(string='Exam Date')
    total_marks = fields.Integer(string='Total Marks')
    passing_marks = fields.Integer(string='Passing Marks')
    obtained_marks = fields.Integer(string='Obtained Marks')

    percentage = fields.Float(
        string='Percentage',
        compute='_compute_marks_result',
        store=True
    )

    result = fields.Selection(
        [
            ('pass', 'Pass'),
            ('fail', 'Fail'),
        ],
        string='Result',
        compute='_compute_marks_result',
        store=True
    )

    grade = fields.Selection(
        [
            ('a_plus', 'A+'),
            ('a', 'A'),
            ('b', 'B'),
            ('c', 'C'),
            ('d', 'D'),
            ('f', 'F'),
        ],
        string='Grade',
        compute='_compute_marks_result',
        store=True
    )

    @api.depends(
        'total_marks',
        'passing_marks',
        'obtained_marks'
    )
    def _compute_marks_result(self):
        for record in self:
            if record.total_marks > 0:
                percentage = (
                    record.obtained_marks / record.total_marks
                ) * 100
            else:
                percentage = 0

            record.percentage = percentage
            if (
                record.total_marks > 0
                and record.obtained_marks >= record.passing_marks
            ):
                record.result = 'pass'
            else:
                record.result = 'fail'
            if percentage >= 90:
                record.grade = 'a_plus'
            elif percentage >= 80:
                record.grade = 'a'
            elif percentage >= 70:
                record.grade = 'b'
            elif percentage >= 60:
                record.grade = 'c'
            elif percentage >= 35:
                record.grade = 'd'
            else:
                record.grade = 'f'
