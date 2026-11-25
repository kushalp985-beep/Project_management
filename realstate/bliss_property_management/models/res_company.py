import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    """Adds last name and first name; name becomes a stored function field."""
    _inherit = "res.company"

    # code = fields.Char("Code", index=True)
    # gender = fields.Selection([('male', 'Male'), ('female', 'Female')],string="Gender")
    # ejari_number = fields.Char(string="Ejari Number")
    # emirateId_number = fields.Char("Emirate ID Number")
    # birthdate = fields.Date(string="Birth Date")
    #
    # arabic_name = fields.Char("Arabic Name")
    # nationality = fields.Many2one('res.country', string="Nationality")
    # passport_number = fields.Char("Passport Number")
    # passport_image = fields.Binary("Passport Image")
    # passport_issue_date = fields.Date("Passport Issue Date")
    # passport_expiration_date = fields.Date("Passport Expiration Date")
    ld_owner_no = fields.Integer(string="LD Owner No")
    _id = fields.Char(string="ID")
    exp_id = fields.Date(string="Expired id")
    pp_no = fields.Char(string="Passport Number")

   

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        partner_model = self.env['res.partner']
        if 'contact_type' not in partner_model._fields:
            return companies
        for company in companies:
            if company.partner_id:
                try:
                    company.partner_id.sudo().write({'contact_type': 'owner'})
                except Exception:
                    _logger.warning(
                        'Could not set contact_type on partner %s for company %s',
                        company.partner_id.id,
                        company.id,
                        exc_info=True,
                    )
        return companies
