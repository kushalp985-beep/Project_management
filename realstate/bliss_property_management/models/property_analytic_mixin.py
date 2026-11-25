# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PropertyAnalyticMixin(models.AbstractModel):
    _name = 'property.analytic.mixin'
    _description = 'Auto-create analytic account for property records'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        readonly=True,
        copy=False,
    )

    def _get_analytic_plan_xmlid(self):
        raise NotImplementedError

    def _get_analytic_account_name(self):
        self.ensure_one()
        return self.display_name or self.name

    def _create_analytic_account(self):
        self.ensure_one()
        plan = self.env.ref(self._get_analytic_plan_xmlid())
        return self.env['account.analytic.account'].create({
            'name': self._get_analytic_account_name(),
            'plan_id': plan.id,
            'company_id': False,
        })

    def _ensure_analytic_account(self):
        for record in self:
            if record.analytic_account_id:
                continue
            record.analytic_account_id = record._create_analytic_account()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ensure_analytic_account()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._ensure_analytic_account()
        name_fields = self._get_analytic_name_fields()
        if name_fields & set(vals.keys()):
            for record in self:
                if record.analytic_account_id:
                    record.analytic_account_id.name = record._get_analytic_account_name()
        return res

    def _get_analytic_name_fields(self):
        return {'name'}
