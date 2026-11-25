from odoo import http
from odoo.http import request

class AttachmentControl(http.Controller):
    
    @http.route(['/web/attachment/<int:id>'], type='http', auth="user", website=True)
    def attachment_common(self, id=None):
        user = request.env.user
        document = request.env['ir.attachment'].browse(id).exists()
        if not document or not document.datas:
            return request.not_found()

        allowed = document.create_uid == user or document.public
        if document.res_model == 'maintenance.request':
            allowed = bool(request.env['maintenance.request'].search([
                ('id', '=', document.res_id),
                '|', '|',
                ('owner_user_id', '=', user.id),
                ('vendor_id', '=', user.partner_id.id),
                ('create_uid', '=', user.id),
            ], limit=1))
        elif document.res_model == 'property.property':
            allowed = bool(request.env['property.property'].search([
                ('id', '=', document.res_id),
                ('landlord_id', '=', user.partner_id.id),
            ], limit=1))
        if not allowed:
            return request.not_found()

        filecontent = document.raw
        filename = document.name

        return request.make_response(
            filecontent,
            headers=[
                ('Content-Type', 'application/octet-stream'),
                ('Content-Disposition', f'attachment; filename="{filename}"')
            ]
        )

