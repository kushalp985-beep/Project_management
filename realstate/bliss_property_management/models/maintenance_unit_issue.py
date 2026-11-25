# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MaintenanceIssueType(models.Model):
    _name = 'maintenance.issue.type'
    _description = 'Maintenance Issue Type'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    subtype_ids = fields.One2many(
        'maintenance.issue.subtype', 'issue_type_id', string='Subtypes')


class MaintenanceIssueSubtype(models.Model):
    _name = 'maintenance.issue.subtype'
    _description = 'Maintenance Issue Subtype'

    name = fields.Char(required=True)
    issue_type_id = fields.Many2one(
        'maintenance.issue.type', string='Issue Type', required=True, ondelete='cascade')
    active = fields.Boolean(default=True)


class MaintenanceUnitIssue(models.Model):
    _name = 'maintenance.unit.issue'
    _description = 'Unit Maintenance Issue'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'complaint_date desc, id desc'

    name = fields.Char(
        string='Reference Number',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('Maintenance.issue.seq'),
    )
    project_id = fields.Many2one('property.project', string='Project', tracking=True)
    maintenance_billing = fields.Selection(
        related='project_id.maintenance_billing',
        string='Maintenance Billing',
        readonly=True,
        store=True,
    )
    building_id = fields.Many2one('property.building', string='Building', tracking=True)
    unit_id = fields.Many2one('property.unit', string='Unit', required=True, tracking=True)
    owner_id = fields.Many2one(
        'res.partner', string='Owner', related='project_id.owner_id', store=True, readonly=True)
    contract_id = fields.Many2one(
        'property.contract',
        string='Contract',
        compute='_compute_contract_id',
        store=True,
        readonly=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='contract_id.contract_currency_id',
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one('res.partner', string='Tenant', tracking=True)
    tenant_name = fields.Char(string='Tenant Name', tracking=True)
    mobile = fields.Char(string='Mobile Number')
    alternate_mobile = fields.Char(string='Alternate Number')
    complaint_date = fields.Date(
        string='Complaint Date', default=fields.Date.context_today, tracking=True)
    completion_date = fields.Date(string='Completion Date', tracking=True, readonly=True)
    description = fields.Text(string='Description / Notes')
    issue_type_id = fields.Many2one('maintenance.issue.type', string='Issue Type', tracking=True)
    issue_subtype_id = fields.Many2one(
        'maintenance.issue.subtype',
        string='Issue Subtype',
        domain="[('issue_type_id', '=', issue_type_id)]",
        tracking=True,
    )
    employee_id = fields.Many2one('hr.employee', string='Assigned Employee', tracking=True)
    resource_calendar_id = fields.Many2one(
        'resource.calendar',
        string='Working Schedule',
        related='employee_id.resource_calendar_id',
        readonly=True,
    )
    before_attachment_ids = fields.Many2many(
        'ir.attachment',
        'maintenance_unit_issue_before_attachment_rel',
        'issue_id',
        'attachment_id',
        string='Before Repair Images',
    )
    after_attachment_ids = fields.Many2many(
        'ir.attachment',
        'maintenance_unit_issue_after_attachment_rel',
        'issue_id',
        'attachment_id',
        string='After Repair Images',
    )
    price = fields.Monetary(
        string='Repairing Charges', currency_field='currency_id', tracking=True)
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True,
        currency_field='currency_id',
    )
    invoice_id = fields.Many2one(
        'account.move', string='Journal Entry', readonly=True, copy=False)
    invoice_count = fields.Integer(compute='_compute_invoice_count')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False, index=True)

    @api.depends('unit_id')
    def _compute_contract_id(self):
        Contract = self.env['property.contract']
        for record in self:
            contract = Contract.browse()
            if record.unit_id:
                contract = Contract.search([
                    ('unit_id', '=', record.unit_id.id),
                    ('state', '=', 'signed'),
                ], limit=1, order='date_start desc')
                if not contract:
                    contract = Contract.search([
                        ('unit_id', '=', record.unit_id.id),
                    ], limit=1, order='date_start desc')
            record.contract_id = contract

    @api.depends('price')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = record.price or 0.0

    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = 1 if record.invoice_id else 0

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.building_id and self.building_id.project_id != self.project_id:
            self.building_id = False
            self.unit_id = False
        elif self.unit_id and self.unit_id.project_id != self.project_id:
            self.unit_id = False

    @api.onchange('building_id')
    def _onchange_building_id(self):
        self.unit_id = False
        if self.building_id and self.building_id.project_id:
            self.project_id = self.building_id.project_id

    @api.onchange('unit_id')
    def _onchange_unit_id(self):
        self.partner_id = False
        self.tenant_name = False
        self.mobile = False
        self.alternate_mobile = False
        if not self.unit_id:
            return
        if self.unit_id.building_id:
            self.building_id = self.unit_id.building_id
        if self.unit_id.project_id:
            self.project_id = self.unit_id.project_id
        contract = self.env['property.contract'].search([
            ('unit_id', '=', self.unit_id.id),
            ('state', '=', 'signed'),
        ], limit=1, order='date_start desc')
        if not contract:
            contract = self.env['property.contract'].search([
                ('unit_id', '=', self.unit_id.id),
            ], limit=1, order='date_start desc')
        if contract and contract.partner_id:
            partner = contract.partner_id
            self.partner_id = partner
            self.tenant_name = partner.name
            # self.mobile = partner.mobile or partner.phone
            # self.alternate_mobile = partner.phone if partner.mobile else False

    @api.onchange('issue_type_id')
    def _onchange_issue_type_id(self):
        if self.issue_subtype_id and self.issue_subtype_id.issue_type_id != self.issue_type_id:
            self.issue_subtype_id = False

    def _link_attachments_to_record(self, attachment_ids):
        if not attachment_ids or not self.ids:
            return
        attachments = self.env['ir.attachment'].browse(attachment_ids).exists()
        attachments.write({
            'res_model': self._name,
            'res_id': self.id,
        })

    def _sync_location_from_unit_vals(self, vals):
        unit_id = vals.get('unit_id')
        if not unit_id:
            return vals
        unit = self.env['property.unit'].browse(unit_id)
        if unit.exists():
            if not vals.get('building_id') and unit.building_id:
                vals['building_id'] = unit.building_id.id
            if not vals.get('project_id'):
                project = unit.project_id or unit.building_id.project_id
                if project:
                    vals['project_id'] = project.id
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals = self._sync_location_from_unit_vals(vals)
        records = super().create(vals_list)
        for record in records:
            record._link_attachments_to_record(record.before_attachment_ids.ids)
            record._link_attachments_to_record(record.after_attachment_ids.ids)
        return records

    def write(self, vals):
        if vals.get('state') == 'done' and 'completion_date' not in vals:
            vals['completion_date'] = fields.Date.context_today(self)
        if vals.get('unit_id'):
            vals = dict(self._sync_location_from_unit_vals(vals))
        res = super().write(vals)
        if 'before_attachment_ids' in vals or 'after_attachment_ids' in vals:
            for record in self:
                record._link_attachments_to_record(record.before_attachment_ids.ids)
                record._link_attachments_to_record(record.after_attachment_ids.ids)
        return res

    def action_assign(self):
        for issue in self:
            if not issue.employee_id:
                raise UserError(_('Please assign an employee before marking as Assigned.'))
            issue.state = 'assigned'

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        for record in self:
            if not record.after_attachment_ids:
                raise UserError(_(
                    'Please upload After Repair Images before marking as Done.'
                ))
            if record.maintenance_billing == 'separate':
                record._validate_separate_maintenance_for_done()
        self.write({
            'state': 'done',
            'completion_date': fields.Date.context_today(self),
        })
        for record in self:
            if record.maintenance_billing == 'separate' and not record.invoice_id:
                record.invoice_id = record._create_maintenance_expense_entry()

    def _get_maintenance_company(self):
        self.ensure_one()
        if self.contract_id:
            return self.contract_id.company_id
        if self.project_id and self.project_id.managed_by:
            return self.project_id.managed_by
        return self.env.company

    def _get_maintenance_analytic_distribution(self):
        self.ensure_one()
        if self.contract_id:
            return self.contract_id._get_invoice_analytic_distribution()
        distribution = {}
        for account in (
            self.project_id.analytic_account_id if self.project_id else False,
            self.building_id.analytic_account_id if self.building_id else False,
            self.unit_id.analytic_account_id if self.unit_id else False,
        ):
            if account:
                distribution[str(account.id)] = 100
        return distribution or False

    def _validate_separate_maintenance_for_done(self):
        self.ensure_one()
        if self.invoice_id:
            raise UserError(_(
                'A maintenance journal entry already exists for this request.'
            ))
        if not self.price:
            raise UserError(_(
                'Please set repairing charges before marking as Done.'
            ))
        company = self._get_maintenance_company()
        if not company.maintenance_expense_account_id:
            raise UserError(_(
                'Please configure Maintenance Expense Account under Accounting '
                'Settings > Maintenance Expense (Separate Billing).'
            ))
        if not company.maintenance_clearing_account_id:
            raise UserError(_(
                'Please configure Maintenance Clearing Account under Accounting '
                'Settings > Maintenance Expense (Separate Billing).'
            ))

    def _get_maintenance_journal(self):
        self.ensure_one()
        company = self._get_maintenance_company()
        if company.specific_journal_id:
            return company.specific_journal_id
        journal = self.env['account.journal'].search([
            ('company_id', '=', company.id),
            ('type', '=', 'general'),
        ], limit=1)
        if not journal:
            raise UserError(_('Please configure a miscellaneous journal for the company.'))
        return journal

    def _create_maintenance_expense_entry(self):
        self.ensure_one()
        company = self._get_maintenance_company()
        currency = self.currency_id or company.currency_id
        expense_account = company.maintenance_expense_account_id
        clearing_account = company.maintenance_clearing_account_id
        analytic = self._get_maintenance_analytic_distribution()
        line_vals = []

        def _line_vals(account, debit, credit, label):
            vals = {
                'account_id': account.id,
                'name': label,
                'debit': debit,
                'credit': credit,
            }
            if analytic:
                vals['analytic_distribution'] = analytic
            return vals

        if self.price:
            line_vals.append(_line_vals(
                expense_account,
                self.price,
                0.0,
                _('Repairing Charges - %s') % self.name,
            ))
        total = currency.round(self.price or 0.0)
        if total:
            line_vals.append(_line_vals(
                clearing_account,
                0.0,
                total,
                _('Maintenance Clearing - %s') % self.name,
            ))
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self._get_maintenance_journal().id,
            'date': self.completion_date or fields.Date.context_today(self),
            'ref': self.name,
            'company_id': company.id,
            'line_ids': [(0, 0, line) for line in line_vals],
        })
        move._post(soft=False)
        return move

    def action_view_maintenance_entry(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_('No maintenance journal entry found.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Maintenance Journal Entry'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
        }

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
