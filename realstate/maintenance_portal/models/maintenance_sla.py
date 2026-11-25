from odoo import models, fields, api


class MaintenanceSla(models.Model):
    _name = 'maintenance.sla'
    _description = 'Maintenance Sla'
    _rec_name = 'name'

    name = fields.Char(required=True, index=True, translate=True)
    description = fields.Html('SLA Policy Description', translate=True)
    active = fields.Boolean('Active', default=True)
    team_id = fields.Many2one('maintenance.team', 'Maintenance Team', required=True)
    tag_ids = fields.Many2many(
        'maintenance.tag', string='Tags')
    stage_id = fields.Many2one(
        'maintenance.stage', 'Target Stage')
    exclude_stage_ids = fields.Many2many(
        'maintenance.stage', string='Excluding Stages', copy=True)
    # priority = fields.Selection(
    #     TICKET_PRIORITY, string='Priority',
    #     default='0', required=True)
    partner_ids = fields.Many2many(
        'res.partner', string="Customers")
    company_id = fields.Many2one('res.company', 'Company', related='team_id.company_id', readonly=True, store=True)
    time = fields.Float('Within', default=0, required=True,
        help='Maximum number of working hours a ticket should take to reach the target stage, starting from the date it was created.')



class MaintenanceTag(models.Model):
    _name = 'maintenance.tag'
    _description = 'Maintenance Tag'  


    name = fields.Char(required=True, index=True)
