from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.tools import lazy

class PropertyContractController(CustomerPortal):
    @http.route('/property_contract/preview/<int:id>', type='http', auth='user',website=True)
    def property_contract_preview(self, id,
        report_type=None,
        access_token=None,
        download=False, **kwargs):
        try:
            contract = self._document_check_access('property.contract', id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(
                model=contract,
                report_type=report_type,
                report_ref='bliss_property_management.action_proposal_report',
                download=download,
            )
        if not contract.exists():
            return request.not_found()

        values = {
            'contract': contract,
            'languages' : lazy(lambda: [lang for
                                      lang in request.env['res.lang'].get_available()
                                      if lang[0] in request.env['ir.http']._get_frontend_langs()])
        }
        return request.render('bliss_property_management.property_contract_preview_template', values)