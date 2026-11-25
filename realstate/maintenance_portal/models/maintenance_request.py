from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MaintenanceStage(models.Model):

    _inherit = 'maintenance.stage'

    submit_vendor = fields.Boolean(string="Submit to Vendor/Internal Responsible")
    date_resolution_submited = fields.Boolean(string="Date of Resolution Submited")
    submited_to_vendor = fields.Boolean(string="Vendor Submited")
    go_ahed_to_vendor = fields.Boolean(string="Go Ahed to Vendor")
    vendor_quotation_submitted = fields.Boolean(string="Vendor Submitted The Quote")
    submit_quote_to_client = fields.Boolean(string="Quote Submitted to Client")

class MaintenanceRequaest(models.Model):
    _inherit = ['maintenance.request','portal.mixin']
    _name = 'maintenance.request'


    code = fields.Char(string="Number",copy=False,default="New")
    partner_id = fields.Many2one('res.partner',string="Partner")
    maintenance_type_id = fields.Many2one('maintenance.type',string="Type")
    vendor_id = fields.Many2one('res.partner',string="Vendor")
    sale_ids = fields.One2many('sale.order','maintenance_id')
    sale_count = fields.Integer(compute="compute_sale_orders")
    date = fields.Date(string="Date")
    property_number = fields.Integer(string="Property Number")
    tenant_details = fields.Char(string="Tenant Details")
    compliant_nature = fields.Char(string="Compliant Nature")
    compliant_desc = fields.Char(string="Compliant Desc")
    attachment = fields.Char(string="Attachment")
    vendor_code = fields.Char(string="Vendor Code")
    vendor_name = fields.Char(string="Vendor Name")
    license_number = fields.Char(string="License Number")
    validity = fields.Char(string="Validity")
    trn_number = fields.Char(string="TRN Number")
    address = fields.Char(string="Address")
    authorized_person = fields.Char(string="Authorized Person")
    email = fields.Char(string="Email Id")
    contact_number = fields.Char(string="Contact Number")
    bank_account = fields.Char(string="Bank Account")
    remarks = fields.Char(string="Remarks")
    submit_to_vendor = fields.Boolean(string="Submit To Vendor",tracking=True)
    go_ahed_to_vendor = fields.Boolean(string="Go Ahead to Vendor",tracking=True,related="stage_id.go_ahed_to_vendor")
    request_confirmed = fields.Boolean(string="Request Confirmed",tracking=True)
    submit_quote_to_client = fields.Boolean()
    is_action_send_to_vendor = fields.Boolean(compute="_compute_send_to_vendor")
    date_resolution = fields.Date(string="Date of Resolution",tracking=True)
    submit_vendor = fields.Boolean(string="Submit to Vendor/Internal Responsible", related="stage_id.submit_vendor", tracking=True)
    vendor_quote_att = fields.Many2one('ir.attachment',string="Vendor Quote",readonly=True)
    vendor_quote_bianry = fields.Binary("Document", attachment=True,related="vendor_quote_att.datas")
    quote_submitted_time = fields.Datetime()
    stage_status = fields.Char(default="draft")
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string="Attachments",
    )
       
    @api.model
    def create(self, vals):
        # Ensure vals is a dict
        if isinstance(vals, models.Model):
            vals = vals.read()[0]

        if not vals.get("code") or vals.get("code") == "New":
            vals["code"] = (
                self.env["ir.sequence"].next_by_code("maintenance.request") or "New"
            )
        mrequest = super(MaintenanceRequaest, self).create(vals)
        mrequest.with_context(no_update=1).stage_status = mrequest.get_stage_status()
        mrequest.with_context(no_update=1).auto_assign_vendor()
        return mrequest
    
    def auto_assign_vendor(self):
        if self.maintenance_type_id and self.maintenance_type_id.vendor_id and self.maintenance_type_id.auto_asign_vendor:
            self.vendor_id = self.maintenance_type_id.vendor_id[0].id
    
    @api.depends('sale_ids')
    def compute_sale_orders(self):
        for rec in self:
            rec.sale_count = len(rec.sale_ids)
    
    def action_view_sale_orders(self):
        self.ensure_one()
        result = self.env['ir.actions.act_window']._for_xml_id('sale.action_orders')
        if len(self.sale_ids) > 1:
            result['domain'] = [('id', 'in', self.sale_ids.ids)]
        elif len(self.sale_ids) == 1:
            result['views'] = [(self.env.ref('sale.view_order_form', False).id, 'form')]
            result['res_id'] = self.sale_ids.id
        else:
            result = {'type': 'ir.actions.act_window_close'}
        if len(self) == 1:
            result['context'] = {
                'default_partner_id': self.owner_user_id.partner_id.id,
                'default_origin': self.name,
                'default_maintenance_id':self.id,
            }
        return result
    
    def write(self,vals):
        rec = super(MaintenanceRequaest,self).write(vals)
        if 'no_update' not in self._context:
            if 'stage_id' in vals:
                self.with_context(no_update=1).stage_status = self.get_stage_status()
        return rec
    
    def get_stage_status(self):
        status = ''
        if self.stage_id.submit_vendor:
            status = 'submit_vendor'
        elif self.stage_id.date_resolution_submited:
            status = 'date_resolution_submited'
        elif self.stage_id.submited_to_vendor:
            status = 'submited_to_vendor'
        elif self.stage_id.go_ahed_to_vendor:
            status = 'go_ahed_to_vendor'
        elif self.stage_id.vendor_quotation_submitted:
            status = 'vendor_quotation_submitted'
        elif self.stage_id.submit_quote_to_client:
            status = 'submit_quote_to_client'
        elif self.stage_id.done:
            status = 'done'
        return status
    
    def check_stage_id(self,field):
        return self.stage_id == self.get_stage_id(field)
    
    def get_stage_id(self,field):
        state = self.env['maintenance.stage'].search([(field,'=',True)],limit=1)
        if not state:
            raise UserError("Next state is not available : %s"%field)
        return state
        
    def _compute_access_url(self):
        super()._compute_access_url()
        for maintenance in self:
            if 'vendor' in self._context:
                maintenance.access_url = '/my/vendor_maintenance/%s' % (maintenance.id)
            else:
                maintenance.access_url = '/my/maintenance/%s' % (maintenance.id)
                
    def action_send_approved(self):
        pass

    # @api.depends("company_id")
    # def _compute_send_to_vendor(self):
    #     for rec in self:
    #         rec.is_action_send_to_vendor = rec.company_id.send_to_vendor

    def action_send_to_vendor(self):
        for vendor in self:
            if not vendor.vendor_id and not vendor.user_id:
                raise UserError("Vendor or responsible user is required!")
            vendor.submit_to_vendor = True
            vendor.stage_id = vendor.get_stage_id("submited_to_vendor").id
            template_id = self.env.ref("maintenance_portal.mail_template_send_to_vendor")
            if self.id:
                template_id.send_mail(self.id)

    def action_go_ahead_to_vendor(self):
        self.stage_id = self.get_stage_id("go_ahed_to_vendor").id
        template_id = self.env.ref("maintenance_portal.mail_template_go_ahead_to_vendor")
        if self.id:
            template_id.send_mail(self.id)
    
    def submit_date_resolution(self):
        self.stage_id = self.get_stage_id("date_resolution_submited").id
    
    def action_generate_quotation(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'views': [(self.env.ref("sale.view_order_form").id, 'form')],
            'view_mode': 'form',
            'target': 'current',
            'name': "Create Quotation",
            'context': {
                'default_partner_id': self.owner_user_id.partner_id.id,
                'default_origin': self.name,
                'default_maintenance_id':self.id
            }
        }

    def action_send_to_client(self):
        self.stage_id = self.get_stage_id("submit_quote_to_client").id
        self.submit_quote_to_client = True
        template_id = self.env.ref("maintenance_portal.mail_template_send_to_client")
        if self.id:
             template_id.send_mail(self.id)

    @api.depends("company_id")  
    def _compute_send_to_vendor(self):
        for rec in self:
            rec.is_action_send_to_vendor = rec.company_id.send_to_vendor
