from odoo import api, fields, models, _ 


class ContractTerminationInspectionWizard(models.TransientModel):
    _name = 'contract.termination.inspection.wizard'
    _description = 'Termination Inspection Wizard'

    contract_term_id = fields.Many2one(
        'contract.termination',
        string="Termination",
        required=True,
        readonly=True
    )

    paint_condition = fields.Selection([
        ('good', 'Good'),
        ('minor_damage', 'Minor Damage'),
        ('major_damage', 'Major Damage'),
    ], string="Paint Condition", required=True)

    paint_remarks = fields.Text(string="Paint Remarks")

    door_condition = fields.Selection([
        ('good', 'Good'),
        ('repair_needed', 'Repair Needed'),
        ('replacement_needed', 'Replacement Needed'),
    ], string="Door Condition", required=True)

    door_remarks = fields.Text(string="Door Remarks")

    # fan_condition = fields.Selection([
    #     ('working', 'Working'),
    #     ('not_working', 'Not Working'),
    # ], string="Fan Condition")

    light_condition = fields.Selection([
        ('working', 'Working'),
        ('not_working', 'Not Working'),
    ], string="Light Condition")

    # ac_condition = fields.Selection([
    #     ('working', 'Working'),
    #     ('not_working', 'Not Working'),
    #     ('not_applicable', 'Not Applicable'),
    # ], string="AC Condition")

    appliance_remarks = fields.Text(string="Other Remarks")

    inspection_attachment_ids = fields.Many2many(
        'ir.attachment',
        string="Inspection Photos"
    )


    def action_confirm_inspection(self):
        
        termination = self.contract_term_id

        termination.write({
            'state_term': 'inspection_checked',
            'is_inspected': True,
            'inspection_cost': 0.0,   
        })

        termination.unit_id.status = "inspection"

        self.env['contract.termination.inspection.line'].create({
            'contract_term_id': termination.id,
            'paint_condition': self.paint_condition,
            'door_condition': self.door_condition,
            # 'fan_condition': self.fan_condition,
            'light_condition': self.light_condition,
            # 'ac_condition': self.ac_condition,
            'appliance_remarks': self.appliance_remarks,
            'inspection_attachment_ids': [(6, 0, self.inspection_attachment_ids.ids)],
        })

        return {'type': 'ir.actions.act_window_close'}

    # def action_confirm_inspection(self):
    #     pass
        # termination = self.contract_term_id

        # termination.write({
        #     'state_term': 'inspection_checked',
        # })

        # termination.unit_id.status = "inspection"

        # return {'type': 'ir.actions.act_window_close'}






