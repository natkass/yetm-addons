{
    'name': 'CRV Print',
    'version': '17.0.1.0',
    'license': 'OPL-1',
    'category': 'Accounting/Accounting',
    'author': 'ETTA Solutions P.L.C.',
    'website': 'https://odooethiopia.com',
    'summary': '''
        Print cash receipt voucher from Accounting -> Customers -> Payments
    ''',
    'depends': [
        'account'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/payment_crv_format.xml',
        'views/crv_format_view.xml',
        'report/print_crv.xml',
    ],
    'installable': True,
}