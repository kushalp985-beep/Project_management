from odoo import models, fields, api


class StudentDashboard(models.Model):
    _name = 'student.dashboard'
    _description = 'Student Dashboard'

    name = fields.Char(
        string='Dashboard Name',
        default='Student Dashboard'
    )
    total_students = fields.Integer(
        string='Total Students',
        compute='_compute_dashboard_data'
    )

    students = fields.Many2many(
    'student.management',
    string='Students',
    compute='_compute_dashboard_data'
    )

    teachers = fields.Many2many(
        'student.teacher',
        string='Teachers',
        compute='_compute_dashboard_data'
    )

    subjects = fields.Many2many(
        'student.subject',
        string='Subjects',
        compute='_compute_dashboard_data'
    )

    standards = fields.Many2many(
        'student.standard',
        string='Standards',
        compute='_compute_dashboard_data'
    )

    marksheets = fields.Many2many(
        'student.marks.sheet',
        string='Marksheets',
        compute='_compute_dashboard_data'
    )

    @api.depends_context('uid')
    def _compute_dashboard_data(self):
        for record in self:
            record.total_students = self.env['student.management'].search_count([])
            record.students = self.env['student.management'].search([])
            record.teachers = self.env['student.teacher'].search([])
            record.subjects = self.env['student.subject'].search([])
            record.standards = self.env['student.standard'].search([])
            record.marksheets = self.env['student.marks.sheet'].search([])


    @api.model
    def get_dashboard_graph_data(self):

        return {
            'students': self.env['student.management'].search_count([]),

            'teachers': self.env['student.teacher'].search_count([]),

            'standards': self.env['student.standard'].search_count([]),

            'subjects': self.env['student.subject'].search_count([]),

            'marksheets': self.env['student.marks.sheet'].search_count([]),
        }
