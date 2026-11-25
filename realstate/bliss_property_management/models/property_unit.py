import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PropertyUnit(models.Model):
    _name = "property.unit"
    _description = "property unit"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'property.analytic.mixin']

    name = fields.Char(string="Code")
    building_id = fields.Many2one('property.building', 'Building')
    owner_id = fields.Many2one(
        'res.partner',
        string='Owner',
        compute='_compute_owner_id',
        store=True,
        readonly=True,
    )


    property_type = fields.Selection(
        [
            ('residential', 'Residential'),
            ('commercial', 'Commercial'),
        ],
        string='Property Type',
        default='commercial',
        required=True,
    )
    project_id = fields.Many2one('property.project', string='Project')
    unit_no = fields.Char(string='Unit No')
    floor_no = fields.Char(string='Floor No')
    unit_usage_id = fields.Many2one('property.unit.usage', 'Unit Usage')
    unit_type_id = fields.Many2one('property.unit.type', 'Unit Type')
    unit_subtype_id = fields.Many2one('property.unit.subtype', 'Unit Subtype')
    status = fields.Selection([('approved', 'Approved'),
                               ('inspection', 'under inspection'),
                               ('maintenance', 'under maintenance'),
                               ], string='Maintenance Status', default='approved')
    suit_area_size = fields.Float(string='Suit Area (Sq. m)')
    total_area_size = fields.Float(string='Total Area (Sq. m)')
    common_area_size = fields.Float(string='Common Area (Sq. m)')
    reference_no = fields.Char(string='Property Reference No')
    approval_ref_no = fields.Char(string='Approval Ref No')
    active = fields.Boolean(string="Active", default=True)
    state = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('booked', 'Booked'),
        ('rented', 'Rented'),
    ], string='State', default='available')
    dewa= fields.Integer(string='DEWA')
    property_ref_number = fields.Char(string='Property Reference Number')
    contract_count = fields.Integer(string='Contracts', compute='_compute_contract_count')
    issue_count = fields.Integer(string='Issues', compute='_compute_issue_count')
    state_id = fields.Many2one('res.country.state', string="State", compute='_compute_state_id', store=True)
    product_id = fields.Many2one('product.product')
    management_fee = fields.Monetary(
        string='Management Fee',
        currency_field='currency_id',
        tracking=True,
        help='Per-unit management fee collected from the owner via Management Fee cheque on Compute Checks.',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='project_id.managed_by.currency_id',
        store=True,
        readonly=True,
    )

    rent_amount = fields.Monetary(string="Rent Amount")

    @api.model
    def create(self,vals):
        rec = super(PropertyUnit,self).create(vals)
        rec.create_products()
        return rec
    
    def write(self,vals):
        rec = super(PropertyUnit,self).write(vals)
        if 'no_update' not in self._context:
            self.with_context(no_update=1).create_products()
        return rec
        
    def create_products(self):
        for rec in self.filtered(lambda x:not x.product_id):
            product = self.env['product.template'].create({'name':rec.name})
            rec.product_id = product.product_variant_id.id

    @api.depends('project_id', 'project_id.owner_id', 'building_id', 'building_id.project_id', 'building_id.project_id.owner_id')
    def _compute_owner_id(self):
        for unit in self:
            project = unit.project_id or unit.building_id.project_id
            unit.owner_id = project.owner_id if project else False

    @api.depends('building_id', 'project_id', 'building_id.project_id')
    def _compute_state_id(self):
        for record in self:
            project = record.building_id.project_id or record.project_id
            record.state_id = project.state_id.id if project else False

    def _compute_contract_count(self):
        for unit in self:
            unit.contract_count = self.env['property.contract'].search_count(
                [('unit_id', '=', unit.id)])

    def _compute_issue_count(self):
        for unit in self:
            unit.issue_count = self.env['maintenance.unit.issue'].search_count(
                [('unit_id', '=', unit.id)])

    def action_view_unit_issues(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Unit Issues',
            'res_model': 'maintenance.unit.issue',
            'view_mode': 'list,form,kanban',
            'domain': [('unit_id', '=', self.id)],
            'context': {'default_unit_id': self.id},
        }

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.building_id and self.building_id.project_id != self.project_id:
            self.building_id = False

    @api.onchange('building_id')
    def _onchange_building_id(self):
        if self.building_id:
            self.project_id = self.building_id.project_id

    def _get_analytic_plan_xmlid(self):
        return 'bliss_property_management.analytic_plan_unit'


class PropertyUnitUsage(models.Model):
    _name = "property.unit.usage"
    _description = "property unit Usage"

    name = fields.Char('Name')


class PropertyUnitType(models.Model):
    _name = "property.unit.type"
    _description = "property unit Type"

    name = fields.Char('Name')


class PropertyUnitSubType(models.Model):
    _name = "property.unit.subtype"
    _description = "property unit SubType"

    name = fields.Char('Name')
