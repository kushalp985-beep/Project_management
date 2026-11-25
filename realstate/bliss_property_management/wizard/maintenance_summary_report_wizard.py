# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MaintenanceSummaryReportWizard(models.TransientModel):
    _name = 'maintenance.summary.report.wizard'
    _description = 'Maintenance Summary Report Wizard'

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    filter_state = fields.Selection(
        [
            ('all', 'All States'),
            ('pending', 'Pending (Draft / Assigned / In Progress)'),
            ('done', 'Completed'),
            ('cancelled', 'Cancelled'),
            ('draft', 'Draft'),
            ('assigned', 'Assigned'),
            ('in_progress', 'In Progress'),
        ],
        string='Status Filter',
        default='all',
        required=True,
    )
    maintenance_billing = fields.Selection(
        [
            ('all', 'All Billing Types'),
            ('included', 'Included Billing'),
            ('separate', 'Separate Billing'),
        ],
        string='Billing Type',
        default='all',
        required=True,
    )
    project_id = fields.Many2one('property.project', string='Project')
    building_id = fields.Many2one(
        'property.building',
        string='Building',
        domain="[('project_id', '=', project_id)]",
    )
    owner_id = fields.Many2one(
        'res.partner',
        string='Owner',
        # domain=[('contact_type', '=', 'owner')],
    )

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.building_id and self.building_id.project_id != self.project_id:
            self.building_id = False
        if self.project_id:
            self.owner_id = self.project_id.owner_id

    def _get_state_domain(self):
        mapping = {
            'pending': [('state', 'in', ('draft', 'assigned', 'in_progress'))],
            'done': [('state', '=', 'done')],
            'cancelled': [('state', '=', 'cancelled')],
            'draft': [('state', '=', 'draft')],
            'assigned': [('state', '=', 'assigned')],
            'in_progress': [('state', '=', 'in_progress')],
        }
        return mapping.get(self.filter_state, [])

    def _get_search_domain(self):
        self.ensure_one()
        domain = list(self._get_state_domain())
        if self.date_from:
            domain.append(('complaint_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('complaint_date', '<=', self.date_to))
        if self.project_id:
            domain.append(('project_id', '=', self.project_id.id))
        if self.building_id:
            domain.append(('building_id', '=', self.building_id.id))
        if self.owner_id:
            domain.append(('owner_id', '=', self.owner_id.id))
        if self.maintenance_billing != 'all':
            domain.append(('maintenance_billing', '=', self.maintenance_billing))
        return domain

    def _get_records(self):
        self.ensure_one()
        return self.env['maintenance.unit.issue'].search(
            self._get_search_domain(),
            order='complaint_date desc, id desc',
        )

    def _get_statistics(self, records):
        states = ('draft', 'assigned', 'in_progress', 'done', 'cancelled')
        counts = {state: 0 for state in states}
        for rec in records:
            if rec.state in counts:
                counts[rec.state] += 1
        total = len(records)
        pending = counts['draft'] + counts['assigned'] + counts['in_progress']
        return {
            'total': total,
            'draft': counts['draft'],
            'assigned': counts['assigned'],
            'in_progress': counts['in_progress'],
            'done': counts['done'],
            'cancelled': counts['cancelled'],
            'pending': pending,
        }

    def _get_filter_labels(self):
        self.ensure_one()
        filter_info = self.fields_get(['filter_state'])['filter_state']
        billing_info = self.fields_get(['maintenance_billing'])['maintenance_billing']
        return {
            'filter_state_label': dict(filter_info.get('selection') or []).get(
                self.filter_state, ''
            ),
            'billing_label': dict(billing_info.get('selection') or []).get(
                self.maintenance_billing, ''
            ),
        }

    def action_print_pdf(self):
        self.ensure_one()
        records = self._get_records()
        if not records:
            raise UserError(_('No maintenance requests found for the selected filters.'))
        labels = self._get_filter_labels()
        return self.env.ref(
            'bliss_property_management.action_maintenance_summary_report'
        ).report_action(
            records,
            data={
                'wizard_id': self.id,
                'record_ids': records.ids,
                'stats': self._get_statistics(records),
                'date_from': self.date_from,
                'date_to': self.date_to,
                'filter_state_label': labels['filter_state_label'],
                'billing_label': labels['billing_label'],
                'report_title': 'Maintenance Summary',
            },
        )
