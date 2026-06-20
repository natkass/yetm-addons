{
"name": "Sales Target VS Achievement",
"version": "17.0.1.2.1",
'category': 'Sales, CRM',
"summary": "Sales Target and Achievements based on Franchisee "
               "target",
"description": """Based on Franchisee's individual target, Sales Target 
    and Achievement calculation for Account Managers""",
'author': '1514 digital',
'company': ' ',
'maintainer': ' ',
'website': " ",
'depends': ['base', "product", 'sale_management', 'mail', 'stock','sale', 'report_xlsx'],
'data': ['security/sales_target_vs_achievement_groups.xml',
             "security/sales_request_security.xml",
             'security/ir.model.access.csv',
             
             'data/sequence.xml',
             
             'views/target_achieve_views.xml',
             'views/account_manager_customer_views.xml',
             'views/franchise_product_category.xml',
             "views/sales_request_views.xml",

             'reports/sales_request_report_template.xml',
             'reports/sales_request_report.xml',

             'wizard/wizard_target_achieve_report_view.xml',
             ],
'images': ['static/description/banner.jpg'],

'assets': {
    'web.assets_backend': [
        'sales_target_vs_achievement/static/src/scss/water_mark.scss',
    ],
},
'license': 'LGPL-3',
'installable': True,
'auto_install': False,
'application': False,
}
