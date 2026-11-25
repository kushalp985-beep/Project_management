# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MaintenanceIssueDashboard(models.Model):
    _name = 'maintenance.issue.dashboard'
    _description = 'Maintenance Issue Dashboard'
    _order = 'sequence'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer(string='Color')
    card_type = fields.Selection([
        ('total', 'Total Issues'),
        ('pending', 'Pending Issues'),
        ('completed', 'Completed Issues'),
        ('invoiced', 'Invoiced (Separate Billing)'),
        ('separate_pending', 'Separate Billing Pending'),
        ('employee', 'Employee-wise Issues'),
    ], required=True)
    issue_count = fields.Integer(compute='_compute_issue_count')

    def _get_issue_domain(self):
        self.ensure_one()
        base = []
        if self.card_type == 'pending':
            return base + [('state', 'in', ('draft', 'assigned', 'in_progress'))]
        if self.card_type == 'completed':
            return base + [('state', '=', 'done')]
        if self.card_type == 'invoiced':
            return base + [
                ('maintenance_billing', '=', 'separate'),
                ('invoice_id', '!=', False),
            ]
        if self.card_type == 'separate_pending':
            return base + [
                ('maintenance_billing', '=', 'separate'),
                ('state', 'in', ('draft', 'assigned', 'in_progress')),
            ]
        return base

    @api.depends('card_type')
    def _compute_issue_count(self):
        Issue = self.env['maintenance.unit.issue']
        for card in self:
            if card.card_type == 'employee':
                issues = Issue.search(card._get_issue_domain())
                card.issue_count = len(issues.mapped('employee_id'))
            else:
                card.issue_count = Issue.search_count(card._get_issue_domain())

    def action_view_issues(self):
        self.ensure_one()
        if self.card_type == 'employee':
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee-wise Issues',
                'res_model': 'maintenance.unit.issue',
                'view_mode': 'graph,pivot,list,form',
                'domain': self._get_issue_domain(),
                'context': {'search_default_group_employee': 1},
            }
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'maintenance.unit.issue',
            'view_mode': 'list,form,kanban',
            'domain': self._get_issue_domain(),
        }
