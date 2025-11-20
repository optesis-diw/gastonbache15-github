# See LICENSE file for full copyright and licensing details.

{
    'name': 'School',
    'version': '15.0.1.0.0',
    'author': 'Serpent Consulting Services Pvt. Ltd.',
    'website': 'http://www.serpentcs.com',
    'category': 'School Management',
    'assets': {
        'web.assets_frontend': [          
            '/school/static/src/scss/schoolcss.scss']},
    'license': "AGPL-3",
    'complexity': 'easy',
    'Summary': 'A Module For School Management',
    'images': ['static/description/EMS.jpg'],
    'depends': ['hr', 'crm', 'account', 'payment_transfer'],
    'data': ['security/school_security.xml',
             'security/ir.model.access.csv',
             'wizard/terminate_reason_view.xml',
             'wizard/wiz_send_email_view.xml',
             'views/student_view.xml',
             'views/school_view.xml',
             'views/teacher_view.xml',
             'views/parent_view.xml',
             'data/student_sequence.xml',
             'wizard/assign_roll_no_wizard.xml',
             'wizard/move_standards_view.xml',
             'views/report_view.xml',
             #'views/template_view.xml',
             'views/identity_card.xml',
             'data/cycle_data.xml',
             'data/subject_gaston.xml',
             'data/niveau_data.xml',

             'views/standard_subject_config_views.xml',
             'data/standard_subject_config.xml',
             
             ],
    'demo': ['demo/school_demo.xml'],
    'installable': True,
    'application': True
}
