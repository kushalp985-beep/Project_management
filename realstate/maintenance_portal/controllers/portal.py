from odoo import http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.tools import groupby as groupbyelem
from odoo.osv.expression import OR, AND
import base64
import json
from datetime import datetime


class MaintenanceCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        user = request.env.user

        MaintenanceRequaest = request.env['maintenance.request']
        if 'maintenance_count' in counters:
            values['maintenance_count'] = MaintenanceRequaest.search_count(self._prepare_maintenance_domain(user))
        return values

    def _prepare_maintenance_domain(self, user):
        return [
            '|',('create_uid','=',user.id),('owner_user_id', '=', user.id)
            # ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            # ('state', '=', 'sent')
        ]
    def _get_maintenance_searchbar_sortings(self):
        return {
            'date': {'label': _('Newest'), 'order': 'id desc'},
            'code': {'label': _('Number'), 'order': 'code'},
            'name': {'label': _('Subject'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'stage_id'},
        }
    
    def _prepare_maintenance_portal_rendering_values(
        self, page=1, date_begin=None, date_end=None, sortby=None, **kwargs
    ):
        MaintenanceRequest = request.env['maintenance.request']
        MaintenanceType = request.env['maintenance.type']
        if not sortby:
            sortby = 'date'

        user = request.env.user
        values = self._prepare_portal_layout_values()

        url = "/my/maintenance"
        domain = self._prepare_maintenance_domain(user)

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        url_args = {'date_begin': date_begin, 'date_end': date_end}
        #
        # if len(searchbar_sortings) > 1:
        #     url_args['sortby'] = sortby

        pager_values = portal_pager(
            url=url,
            total=MaintenanceRequest.search_count(domain),
            page=page,
            step=self._items_per_page,
            url_args=url_args,
        )
        
        searchbar_sortings = self._get_maintenance_searchbar_sortings()
        sort_order = searchbar_sortings[sortby]['order']
        
        requests = MaintenanceRequest.search(domain, order=sort_order, limit=self._items_per_page, offset=pager_values['offset'])
        property_history = request.env['property.history'].search([('tenant_id','=',user.partner_id.id),('start_date','<=',datetime.now()),('end_date','>',datetime.now())])
        properties = property_history.mapped('property_id')
        maintenance_type = MaintenanceType.search([])
        values.update({
            'date': date_begin,
            'maintenance_requests': requests.sudo(),
            'page_name': 'maintenance',
            'properties': properties, 
            'maintenance_type': maintenance_type, 
            'pager': pager_values,
            'default_url': url,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        request.session['my_maintenance_request_history'] = values['maintenance_requests'].ids[:100]

        # if len(searchbar_sortings) > 1:
        #     values.update({
        #         'sortby': sortby,
        #         'searchbar_sortings': searchbar_sortings,
        #     })

        return values

    @http.route(['/my/maintenance', '/my/maintenance/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_maintenance(self, **kwargs):
        values = self._prepare_maintenance_portal_rendering_values(**kwargs)
        return request.render("maintenance_portal.portal_my_maintenance_requests", values)

    @http.route(['/maintenance/create'], type='http', auth="user", methods=['POST', 'GET'], website=True)
    def create_maintenance_request(self, **kwargs):
        user = request.env.user
        property_history = request.env['property.history'].search([
            ('tenant_id', '=', user.partner_id.id),
            ('start_date', '<=', datetime.now()),
            ('end_date', '>', datetime.now()),
        ])
        properties = property_history.mapped('property_id')
        maintenance_type = request.env['maintenance.type'].search([])
        attachment = request.env['ir.attachment']
        if request.httprequest.method == 'POST':
            property_id = int(kwargs.get('property_id')) if kwargs.get('property_id') else False
            if property_id and property_id not in properties.ids:
                return request.redirect('/my/maintenance')
            maintenance_request = request.env['maintenance.request'].create({
                'name': kwargs.get('name'),
                'property_id': property_id,
                'maintenance_type_id': int(kwargs.get('maintenance_type_id')) if kwargs.get('maintenance_type_id') else False,
                'date': kwargs.get('date'),
                'description': kwargs.get('remarks'),
                'owner_user_id':request.env.user.id
            })
            uploaded_files = request.httprequest.files.getlist('attachments')
            seen_hashes = set()
            attachment = request.env['ir.attachment']
            for file in uploaded_files:
                if file and file.filename:
                    image_data = file.read()
                    image_hash = hash(image_data)
                    if image_hash not in seen_hashes:
                        seen_hashes.add(image_hash)
                        attachment += request.env['ir.attachment'].create({
                            'name': file.filename,
                            'datas': base64.b64encode(image_data).decode('utf-8'),  # Base64 encoded file data
                            'res_model': maintenance_request._name,
                            'res_id': maintenance_request.id,
                            'type': 'binary',
                            'res_field':'attachment_ids'
                        })
            maintenance_request.attachment_ids = [(6,0,attachment.ids)]
            if maintenance_request:
                return request.redirect('/my/maintenance')
        return request.render('maintenance_portal.template_maintenance_form', {
            'properties': properties,
            'maintenance_type':maintenance_type,
            'attachment_ids':attachment,
        })
    
    @http.route(['/my/maintenance/<int:maintenance_id>'], type='http', auth="public", website=True)
    def portal_maintenance_page(
        self,
        maintenance_id,
        access_token=None,
        **kw
    ):
        try:
            maintenance_request = self._document_check_access('maintenance.request', maintenance_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'maintenance_request': maintenance_request,
            'report_type': 'html',
            'res_company': maintenance_request.company_id,
        }

        history_session_key = 'my_maintenance_request_history'

        values = self._get_page_view_values(
            maintenance_request, access_token, values, history_session_key, False)
        return request.render('maintenance_portal.template_maintenance_form', values)
