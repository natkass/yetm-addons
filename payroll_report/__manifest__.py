{
    'name': 'Payrolll',
    'version': '1.0',
    'summary': 'Manage employee payroll',
    'description': """
        Payroll Management
        ==================
        This module provides features to manage employee payroll including salary computation, payslip generation, and tax calculation.
    """,
    'author': 'Nuredin Muhamed',
    'website': 'http://www.yourcompany.com',
    'category': 'Human Resources',
    'depends': ['base', 'hr'],
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/payroll_view.xml',
        # 'views/res_config_settings_views.xml',
        'report/report.xml',
        'report/report_template.xml',
    ],
    'demo': [
        # 'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
