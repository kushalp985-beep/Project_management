import logging

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    """Adds last name and first name; name becomes a stored function field."""

    _inherit = "res.partner"

    code = fields.Char("Code", index=True)
    contact_type = fields.Selection([('owner', 'Owner'),('tenant', 'Tenant'),('inter', 'Internal')], 'Type',default='tenant')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string="Gender")
    ejari_number = fields.Char(string="Ejari Number")
    birthdate = fields.Date(string="Birth Date")

    arabic_name = fields.Char("Arabic Name")
    nationality = fields.Many2one('res.country',string="Nationality")
    passport_number = fields.Char("Passport Number")
    passport_image = fields.Binary("Passport Image")
    passport_issue_date = fields.Date("Passport Issue Date")
    passport_expiration_date = fields.Date("Passport Expiration Date")


    emirateId_image = fields.Binary("Emirate ID Image")
    emirateId_issue_date = fields.Date("Emirate ID Issue Date")
    emirateId_expiration_date = fields.Date("Emirate ID Expiration Date")
    emirateId_number = fields.Char("Emirate ID Number")

    visa_issue_date = fields.Date("Visa Issue Date")
    visa_expiration_date = fields.Date("Visa Expiration Date")


    contract_count = fields.Integer(string='Contracts', compute='_compute_contract_count')

    def _compute_contract_count(self):
        for partner in self:
            partner.contract_count = self.env['property.contract'].search_count(
                [('partner_id', '=', partner.id)])




