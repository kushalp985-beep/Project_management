{
    'name': 'Student Management',
    'version': '18.0.0.1',
    'depends': ['base', 'mail'],
    'data': [
    #   'security/security.xml',
      'security/ir.model.access.csv',
    #   'views/data/student.sequence.xml',
      'views/student_views.xml',
      'views/standard_views.xml',
      'views/marks_sheet_views.xml',
      'views/subject_views.xml',
      'views/teacher_views.xml',
      'models/wizard/student_wizard_views.xml',
      # 'views/student_document_views.xml'
      'report/student_report.xml',
      'report/student_report_action.xml',
      'report/student_email_template.xml',
      'data/student_birthday_cron.xml',
      'views/student_dashboard_views.xml'
],  
      'assets': {
        'web.assets_backend': [
          'student_management/static/src/js/student_dashboard.js',
          'student_management/static/src/xml/student_dashboard.xml',
    ],
},
  
    'installable': True,
    'application': True,
}
