from odoo import models, fields, api, tools

class PropertyUnitMedia(models.Model):
    _name = 'property.unit.media'
    _description = "Property Unit Media"
    _inherit = ['image.mixin']
    _order = 'sequence, id'

    name = fields.Char("Name", required=True)
    sequence = fields.Integer(default=10)
    image_1920 = fields.Image()
    contract_id = fields.Many2one('property.contract', "Property Contract", index=True, ondelete='cascade')

    can_image_1024_be_zoomed = fields.Boolean("Can Image 1024 be zoomed", compute='_compute_can_image_1024_be_zoomed', store=True)

    @api.depends('image_1920', 'image_1024')
    def _compute_can_image_1024_be_zoomed(self):
        for media in self:
            media.can_image_1024_be_zoomed = media.image_1920 and tools.is_image_size_above(media.image_1920, media.image_1024)

    @api.model_create_multi
    def create(self, vals_list):
        context_without_unit = self.with_context({k: v for k, v in self.env.context.items() if k != 'default_contract_id'})
        normal_vals = []
        unit_vals_list = []

        for vals in vals_list:
            if vals.get('contract_id') and 'default_contract_id' in self.env.context:
                unit_vals_list.append(vals)
            else:
                normal_vals.append(vals)

        return super().create(normal_vals) + super(PropertyUnitMedia, context_without_unit).create(unit_vals_list)