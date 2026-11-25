import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PropertyProject(models.Model):

    _name = "property.project"
    _description = "property project"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'property.analytic.mixin']

    name = fields.Char(string="Project Name")
    owner_id = fields.Many2one(
        'res.partner',
        string='Owner',
        domain=[('contact_type', '=', 'owner')],
        tracking=True,
    )
    managed_by = fields.Many2one("res.company", string="Managed By",readonly=True,default=lambda self: self.env.company)
    # maintained_by = fields.Many2one("res.company", string="Maintained By")
    state_id = fields.Many2one("res.country.state", string="Emirate")
    city_id = fields.Many2one('res.city', 'Area')
    active = fields.Boolean(string="Active", default=True)
    building_ids = fields.One2many(
        'property.building', 'project_id', string='Buildings')
    building_count = fields.Integer(
        string='Buildings', compute='_compute_building_count')
    maintenance_billing = fields.Selection(
        [
            ('included', 'Included in Rent'),
            ('separate', 'Separate Maintenance Invoice'),
        ],
        string='Maintenance Billing',
        default='included',
        required=True,
        tracking=True,
        help='Included: maintenance cost in rent, no separate invoice. '
             'Separate: use Maintenance menu with vendor invoice and owner settlement.',
    )
    @api.depends('building_ids')
    def _compute_building_count(self):
        for project in self:
            project.building_count = len(project.building_ids)

    def _get_analytic_plan_xmlid(self):
        return 'bliss_property_management.analytic_plan_project'

