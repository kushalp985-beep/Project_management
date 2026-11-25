import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class SecurityDeposit(models.Model):
    _name = "property.security.deposit"
    _description = "security deposit model"


    contract_term_id = fields.Many2one('contract.termination', string='Contract termination')
    name = fields.Char(string='name')
    partner_id = fields.Many2one('res.partner', string='Tenant', required=True, related='contract_term_id.contract_id.partner_id')
    security_dep = fields.Monetary(string='Security deposit', related='contract_term_id.contract_id.security_deposit', currency_field='contract_currency_id')
    contract_currency_id = fields.Many2one(string='Currency', related="contract_term_id.contract_currency_id", store=True, readonly=True)

