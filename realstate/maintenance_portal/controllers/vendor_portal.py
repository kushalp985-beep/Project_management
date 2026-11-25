import base64
from datetime import datetime

from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

class VendorMaintenanceCustomerPortal(CustomerPortal):
    def _get_vendor_request(self, maintenance_id):
        req = request.env['maintenance.request'].search([
            ('id', '=', maintenance_id),
            '|', ('vendor_id', '=', request.env.user.partner_id.id), ('user_id', '=', request.env.user.id),
            ('submit_to_vendor', '=', True),
        ], limit=1)
        return req

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        user = request.env.user

        MaintenanceRequaest = request.env['maintenance.request']
        if 'vendor_maintenance' in counters:
            values['vendor_maintenance'] = MaintenanceRequaest.search_count(self._prepare_vendor_maintenance_domain(user))
        return values

    def _prepare_vendor_maintenance_domain(self, user):
        return [
            '|',('vendor_id', '=', user.partner_id.id),('user_id', '=', user.id),
            ('submit_to_vendor','=',True)
        ]

    # def _get_sale_searchbar_sortings(self):
    #     return {
    #         'date': {'label': _('Order Date'), 'order': 'date_order desc'},
    #     }

    def _prepare_vendor_maintenance_portal_rendering_values(
        self, page=1, date_begin=None, date_end=None, sortby=None, **kwargs
    ):
        MaintenanceRequest = request.env['maintenance.request']

        if not sortby:
            sortby = 'date'

        user = request.env.user
        values = self._prepare_portal_layout_values()

        url = "/my/vendor_maintenance"
        domain = self._prepare_vendor_maintenance_domain(user)

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        url_args = {'date_begin': date_begin, 'date_end': date_end}

        pager_values = portal_pager(
            url=url,
            total=MaintenanceRequest.search_count(domain),
            page=page,
            step=self._items_per_page,
            url_args=url_args,
        )
        requests = MaintenanceRequest.search(domain, order='id', limit=self._items_per_page, offset=pager_values['offset'])

        values.update({
            'date': date_begin,
            'maintenance_requests': requests,
            'page_name': 'vendor_maintenance',
            'pager': pager_values,
            'default_url': url,
        })
        return values

    @http.route(['/my/vendor_maintenance', '/my/vendor_maintenance/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_vendor_maintenance(self, **kwargs):
        values = self._prepare_vendor_maintenance_portal_rendering_values(**kwargs)
        return request.render("maintenance_portal.portal_my_vendor_maintenance_requests", values)

    @http.route(['/my/vendor_maintenance/<int:maintenance_id>'], type='http', auth="public", website=True)
    def portal_vendor_maintenance_page(
            self,
            maintenance_id,
            access_token=None,
            **kw
    ):
        try:
            maintenance_request = self._document_check_access('maintenance.request', maintenance_id,
                                                              access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'vendor_maintenance_request': maintenance_request,
            'report_type': 'html',
            'res_company': maintenance_request.company_id,
        }

        history_session_key = 'my_maintenance_request_history'

        values = self._get_page_view_values(
            maintenance_request, access_token, values, history_session_key, False)

        return request.render('maintenance_portal.template_vendor_maintenance_form', values)

    @http.route(['/vendor_maintenance/date_resolution/<int:maintenance_id>'], type='http', auth="user",methods=['POST', 'GET'], website=True)
    def put_date_resolution_maintenance_request(self, maintenance_id=None,access_token=None,**kwargs):
        maintenance_request = self._get_vendor_request(maintenance_id)
        if not maintenance_request:
            return request.redirect('/my/vendor_maintenance')
        if request.httprequest.method == 'POST':
            maintenance_request.write({
                'date_resolution':kwargs.get('date_resolution')
            })
            maintenance_request.submit_date_resolution()
        return request.redirect("/my/vendor_maintenance/%s?access_token=%s"%(maintenance_request.id,access_token))
    
    @http.route(['/vendor_maintenance/request_done/<int:maintenance_id>'], type='http', auth="user",methods=['POST', 'GET'], website=True)
    def request_done_maintenance_request(self, maintenance_id=None,access_token=None,**kwargs):
        maintenance_request = self._get_vendor_request(maintenance_id)
        if not maintenance_request:
            return request.redirect('/my/vendor_maintenance')
        maintenance_request.stage_id = maintenance_request.get_stage_id('done')
        return request.redirect("/my/vendor_maintenance/%s?access_token=%s"%(maintenance_request.id,access_token))
        
    @http.route(['/vendor_maintenance/attach_quote/<int:maintenance_id>'], type='http', auth="user",methods=['POST', 'GET'], website=True)
    def attach_quote_maintenance_request(self, maintenance_id=None,access_token=None,**kwargs):
        maintenance_request = self._get_vendor_request(maintenance_id)
        if not maintenance_request:
            return request.redirect('/my/vendor_maintenance')
        upload = request.httprequest.files.get('quotation_data')
        if not upload:
            return request.redirect("/my/vendor_maintenance/%s?access_token=%s" % (maintenance_request.id, access_token))
        attachment = request.env['ir.attachment'].create({
            'name': upload.filename,
            'datas': base64.b64encode(upload.read()).decode('utf-8'),
            'res_model': maintenance_request._name,
            'res_id': maintenance_request.id,
            'type': 'binary',
            'res_field':'vendor_quote_att'
        })
        maintenance_request.write({
            'quote_submitted_time':datetime.now(),
            'vendor_quote_att':attachment.id,
            'stage_id':maintenance_request.get_stage_id('vendor_quotation_submitted').id
        })
        return request.redirect("/my/vendor_maintenance/%s?access_token=%s"%(maintenance_request.id,access_token))
    

