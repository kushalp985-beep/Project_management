# -*- coding: utf-8 -*-
import json

from odoo import api, models

DEFAULT_STATE_LABELS = {
    'draft': 'Draft',
    'assigned': 'Assigned',
    'in_progress': 'In Progress',
    'done': 'Done',
    'cancelled': 'Cancelled',
}
DEFAULT_BILLING_LABELS = {
    'included': 'Included in Rent',
    'separate': 'Separate Maintenance Invoice',
}


class MaintenanceSummaryReport(models.AbstractModel):
    _name = 'report.bliss_property_management.maintenance_summary_report'
    _description = 'Maintenance Summary PDF Report'

    @api.model
    def _parse_report_data(self, data):
        """Normalize wizard data passed via report URL query string."""
        result = dict(data or {})
        for key in ('record_ids', 'stats'):
            val = result.get(key)
            if isinstance(val, str):
                try:
                    result[key] = json.loads(val)
                except (json.JSONDecodeError, TypeError, ValueError):
                    if key == 'record_ids' and val:
                        result[key] = [
                            int(x) for x in val.split(',') if str(x).strip().isdigit()
                        ]
        if result.get('wizard_id') and isinstance(result['wizard_id'], str):
            try:
                result['wizard_id'] = int(result['wizard_id'])
            except ValueError:
                pass
        return result

    @api.model
    def _get_report_values(self, docids, data=None):
        data = self._parse_report_data(data)
        docids = docids or data.get('record_ids') or []
        records = self.env['maintenance.unit.issue'].browse(docids).exists()
        if not records and data.get('record_ids'):
            records = self.env['maintenance.unit.issue'].browse(data['record_ids']).exists()

        wizard = self.env['maintenance.summary.report.wizard'].browse(
            data.get('wizard_id')
        ).exists()

        stats = data.get('stats') or {}
        if isinstance(stats, dict) and not stats and wizard:
            stats = wizard._get_statistics(records)
        elif isinstance(stats, dict) and not stats and records:
            stats = self.env['maintenance.summary.report.wizard']._get_statistics(
                records
            )
        if not isinstance(stats, dict):
            stats = {}

        state_labels = dict(DEFAULT_STATE_LABELS)
        billing_labels = dict(DEFAULT_BILLING_LABELS)
        try:
            issue_fields = self.env['maintenance.unit.issue'].fields_get(
                ['state', 'maintenance_billing']
            )
            state_labels.update(dict(issue_fields['state'].get('selection') or []))
            billing_labels.update(
                dict(issue_fields['maintenance_billing'].get('selection') or [])
            )
        except (KeyError, TypeError):
            pass

        filter_state_label = data.get('filter_state_label', '')
        billing_label = data.get('billing_label', '')
        if wizard and not filter_state_label:
            filter_info = wizard.fields_get(['filter_state'])['filter_state']
            filter_state_label = dict(filter_info.get('selection') or []).get(
                wizard.filter_state, ''
            )
        if wizard and not billing_label:
            billing_info = wizard.fields_get(['maintenance_billing'])['maintenance_billing']
            billing_label = dict(billing_info.get('selection') or []).get(
                wizard.maintenance_billing, ''
            )

        return {
            'doc_ids': records.ids,
            'doc_model': 'maintenance.unit.issue',
            'docs': records,
            'records': records,
            'stats': stats,
            'state_labels': state_labels,
            'billing_labels': billing_labels,
            'report_title': data.get('report_title', 'Maintenance Summary'),
            'date_from': data.get('date_from') or (wizard.date_from if wizard else False),
            'date_to': data.get('date_to') or (wizard.date_to if wizard else False),
            'filter_state_label': filter_state_label,
            'billing_label': billing_label,
        }
