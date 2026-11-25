{
    'name': 'Student Alternate Address',
    'version': '18.0.1.0.0',
    'summary': 'Add alternate address to student',
    'category': 'Education',
    'depends': ['base', 'student_management', 'sale_management'],
    'data': [
        'views/student_views.xml',
        'views/sale_order_views.xml',
        'views/sale_order_line_views.xml',
        'views/res_config_settings_views.xml',
],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
