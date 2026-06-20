{
    'name': 'ERCA Monthly Tax Report',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Generate Monthly Tax Report for ERCA from Vendor Bills',
    'depends': ['base', 'account', 'report_xlsx'],
    'data': [
        'wizard/erca_report_wizard_view.xml',
        'wizard/customer_tax_wizard_view.xml',
        'views/report.xml',
    ],
    'installable': True,
    'application': False,
}