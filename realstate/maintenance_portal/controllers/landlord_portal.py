from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

class LandlorCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        user = request.env.user

        propertyObj = request.env['property.property']
        if 'landlord' in counters:
            values['landlord'] = propertyObj.search_count(self._prepare_landlord_domain(user))
        return values

    def _prepare_landlord_domain(self, user):
        return [
            ('landlord_id', '=', user.partner_id.id)
        ]

    # def _get_sale_searchbar_sortings(self):
    #     return {
    #         'date': {'label': _('Order Date'), 'order': 'date_order desc'},
    #     }

    def _prepare_landlord_portal_rendering_values(
        self, page=1, date_begin=None, date_end=None, sortby=None, **kwargs
    ):
        propertyObj = request.env['property.property']

        if not sortby:
            sortby = 'date'

        user = request.env.user
        values = self._prepare_portal_layout_values()

        url = "/my/landlord"
        domain = self._prepare_landlord_domain(user)


        url_args = {}

        pager_values = portal_pager(
            url=url,
            total=propertyObj.search_count(domain),
            page=page,
            step=self._items_per_page,
            url_args=url_args,
        )
        requests = propertyObj.search(domain, order='id', limit=self._items_per_page, offset=pager_values['offset'])

        values.update({
            'date': date_begin,
            'properties': requests,
            'page_name': 'landlord',
            'pager': pager_values,
            'default_url': url,
        })
        return values

    @http.route(['/my/landlord', '/my/landlord/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_landlord(self, **kwargs):
        values = self._prepare_landlord_portal_rendering_values(**kwargs)
        return request.render("maintenance_portal.portal_my_landlord_requests", values)

    @http.route(['/my/landlord/<int:property_id>'], type='http', auth="public", website=True)
    def portal_landlord_page(
            self,
            property_id,
            access_token=None,
            **kw
    ):
        try:
            property = self._document_check_access('property.property', property_id,
                                                              access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'property': property,
            'report_type': 'html'
        }

        history_session_key = 'my_property_request_history'

        values = self._get_page_view_values(
            property, access_token, values, history_session_key, False)

        return request.render('maintenance_portal.portal_my_landlord_requests_form', values)

