import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PropertyBuilding(models.Model):

    _name = "property.building"
    _description = "property building"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'property.analytic.mixin']
    _rec_name = "building_name"

    name = fields.Char(string="Code")
    owner_id = fields.Many2one(
        'res.partner', related='project_id.owner_id', string='Owner', store=True)
    project_id = fields.Many2one(
        'property.project', string='Project', required=True, ondelete='restrict')
    hold_type_id = fields.Selection(
        [('free', 'Free Hold'), ('nonfree', 'Non Free Hold')],
        string='Hold Type', default='free')
    state_id = fields.Many2one(
        'res.country.state', string='Emirate', related='project_id.state_id', store=True, readonly=True)
    city_id = fields.Many2one(
        'res.city', string='Area', related='project_id.city_id', store=True, readonly=True)
    land_no_id = fields.Char('Land No')
    municipality_no = fields.Char('Municipality No')
    building_name = fields.Char('Building Name')
    arabic_name = fields.Char('Arabic Name')
    ejari_building_name = fields.Char('Ejari Building Name')
    ejari_building_name_arabic = fields.Char('Ejari Building Name Arabic')
    address = fields.Char('Address')
    unit_count = fields.Integer('Unit Count')
    completion_date = fields.Date('Completion Date')
    building_usage_ids = fields.Many2many('property.building.usage', string='Building Usage')
    building_type_id = fields.Many2one('property.building.type', 'Building Type')
    floor_count = fields.Integer('Floor Count')
    parking_count = fields.Integer('Parking Count')
    buid_area_size = fields.Float('Buid Area (Sq. m)')
    plot_area_size = fields.Float('Plot Area (Sq. m)')
    leasable_area_size = fields.Float('Leasable Area (Sq. m)')
    commom_area_size = fields.Float('Commom Area (Sq. m)')
    ejari_building_area_size = fields.Float('Ejari Building Area (Sq. m)')
    ejari_common_area_size = fields.Float('Ejari Common Area (Sq. m)')
    ejari_leasable_area_size = fields.Float('Ejari Leasable Area (Sq. m)')
    status = fields.Selection([('approved', 'Approved'), ], 'Status')
    reference_number = fields.Char('Property Reference Number')
    approval_ref_no = fields.Char('Approval Ref No')
    active = fields.Boolean('Active',default=True)
    dewa = fields.Integer('Dewa')
    facilities = fields.Many2many('property.facilities', string='Facilities')
    unit_ids = fields.One2many('property.unit', 'building_id', string='Units')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        project_id = self.env.context.get('default_project_id')
        if project_id and 'project_id' in fields_list:
            res['project_id'] = project_id
        return res

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id:
            self.owner_id = self.project_id.owner_id

    def _get_analytic_plan_xmlid(self):
        return 'bliss_property_management.analytic_plan_building'

    def _get_analytic_account_name(self):
        self.ensure_one()
        return self.building_name or self.name or super()._get_analytic_account_name()

    def _get_analytic_name_fields(self):
        return {'name', 'building_name'}


class PropertyBuildingUsage(models.Model):

    _name = "property.building.usage"
    _description = "property building Usage"

    name = fields.Char('Name')
class PropertyBuildingType(models.Model):

    _name = "property.building.type"
    _description = "property building Type"

    name = fields.Char('Name')