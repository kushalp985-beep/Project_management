import logging

from odoo import api, fields, models
from datetime import timedelta

_logger = logging.getLogger(__name__)


class ContractRenewal(models.Model):
    _name = "contract.renewal"
    _description = "contract renewal model"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    code_renew = fields.Char(string="Code", required=True,
                             default=lambda self: self.env['ir.sequence'].next_by_code('Contract.renew.seq.code'))
    state_renew = fields.Selection([
        ("rcnew", "New"),
        ("rcrapproved", "Renewal Approved"),
        ("rcdone", "Renewal Done"),
    ], string="Status", tracking=True, copy=False, index=True, default='rcnew')

    renew_value = fields.Monetary(string="Renew Value", currency_field='contract_currency_id')
    rera_value = fields.Monetary(string="Rera Value",compute='_compute_rera_value',readonly=True, currency_field='contract_currency_id')
    date_start = fields.Date(string="Start Date", related="contract_id.date_start", readonly=True)
    date_stop = fields.Date(string="Stop Date", related="contract_id.date_stop", readonly=True)
    start_date_from = fields.Date(string="Start From", related="contract_id.start_date_from", readonly=True)
    add_extra_deposit = fields.Boolean(string="Add extra security deposit", default=False)
    extra_security_deposit = fields.Float(string="Extra_security_deposit")
    contract_id = fields.Many2one('property.contract', string="Contract")
    unit_id = fields.Many2one('property.unit', string="Unit", related='contract_id.unit_id', store=True, readonly=False)
    new_contract_id = fields.Many2one('property.contract',string='New Contract Code',readonly=True)
    contract_currency_id = fields.Many2one(string='Currency', related="contract_id.contract_currency_id", store=True, readonly=True)


    @api.depends('contract_id.value')
    def _compute_rera_value(self):
        for record in self:
            record.rera_value = record.contract_id.value + (0.10 * record.contract_id.value)

    def action_approve_renewal(self):
        self.write({'state_renew': 'rcrapproved'})

    def action_done_renewal(self):
        for record in self:
            contract = record.contract_id
            new_contract = contract.copy({
                'code': self.code_renew,
                'date_start': record.date_start,
                'date_stop': record.date_stop,
                'start_date_from': record.start_date_from,
                # 'extra_security_deposit': record.extra_security_deposit,
                'value': record.renew_value,
                'commission_value': 0
            })
            record.new_contract_id = new_contract.id
            record.write({'state_renew': 'rcdone'})
            record.contract_id.state = 'renewed'
            record.contract_id.unit_id.state = 'booked'
            record.new_contract_id.state = 'contract'

        return True
