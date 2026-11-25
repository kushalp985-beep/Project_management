from odoo import models, fields, api, _

class ResUsers(models.Model):
    _inherit = 'res.users'

    main_type = fields.Selection([('vendor', 'Vendor'),('normal', 'Normal')],string="Maintenance Type")

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_vendor = fields.Boolean(string="Is vendor")
    is_client = fields.Boolean(string="Is Client")


class ResCompany(models.Model):
    _inherit = 'res.company'

    send_to_vendor = fields.Boolean(
        string="Send Maintenance to Vendor",
        help="If enabled, maintenance requests will be automatically sent to vendors."
    )    
