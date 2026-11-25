# -*- coding: utf-8 -*-

{
    'name': 'Maintenance Portal',
    'version': '19.0.1.0.0',
    'category': '',
    "license": "OPL-1",
    'summary': 'Maintenance Portal',
    'description': """ Maintenance Portal """,
    'depends': ['maintenance','portal','sale'],
    'data': [
        "security/ir.model.access.csv",
        "security/res_groups.xml",
        "data/mail_send_to_client.xml",
        "data/mail_send_to_vendor.xml",
        "data/mail_quotation_generate.xml",
        "data/mail_go_ahead_to_vendor.xml",
        "data/ir_sequence_data.xml",
        'views/maintenance_portal_template_view.xml',
        'views/maintenance_request_view.xml',
        'views/vendor_portal_template_view.xml',
        'views/res_user_view.xml',
        'views/maintenance_sla_view.xml',
        'views/maintenance_type_view.xml',
        'views/maintenance_vendor_view.xml',
        'views/landlord_portal.xml'
    ],
    'assets': {
        'web.assets_frontend': [
            'maintenance_portal/static/src/js/create_maintenance_portal.js',
        ],
    },
    'application': False,
    'installable': True,
    'auto_install': False,
}
