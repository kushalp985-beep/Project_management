from odoo import models, fields, api

class PropertyContractStage(models.Model):
    _name = "property.contract.stage"
    _description = "Property Contract Stage"
    _order = "sequence"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean("Folded in Kanban")
    color = fields.Integer("Color")
    
    contract_count = fields.Integer(compute="_compute_contract_count")

    def _compute_contract_count(self):
        for stage in self:
            stage.contract_count = self.env["property.contract"].search_count(
                [("stage_id", "=", stage.id)]
            )

    state = fields.Selection([
        ("proposal", "Proposal"),
        ("pwaiting", "Waiting for approval"),
        ("papproved", "Proposal Approved"),
        ("psent", "Proposal Sent"),
        ("pconfirmed", "Proposal confirmed"),
        ("prejected", "Proposal rejected"),
        ("contract", "New Contract"),
        ("csent", "Contract Sent"),
        ("cconfirmed", "Confirmed"),
        ("clegalapproved", "Legal approved"),
        ("signed", "Signed"),
        ("canceled", "Canceled"),
        ("berenew", "To be renew"),
        ("renewed", "Renewed"),
        ("ctermination", "Termination"),
    ], required=True)
    
    
    # def action_view_contracts(self):
    #     self.ensure_one()
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Contracts',
    #         'res_model': 'property.contract',
    #         'view_mode': 'list,form',
    #         'domain': [('stage_id', '=', self.id)],
    #     }
        
    def action_view_contracts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contracts',
            'res_model': 'property.contract',
            'view_mode': 'list,form',
            'domain': [('stage_id', '=', self.id)],
            'context': {'default_stage_id': self.id},
        }

    def action_create_contract(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Contract',
            'res_model': 'property.contract',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_stage_id': self.id},
        }