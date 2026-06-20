# -*- coding: utf-8 -*-
{
    'name': 'POS Hide Session Control Table',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Hide Expected/Counted/Difference table from POS Sales Details Report',
    'description': """
        This module hides the payment control table (Expected, Counted, Difference columns)
        from the POS Sales Details report while keeping the Session Control heading,
        total amount, number of transactions, and session notes visible.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['point_of_sale'],
    'data': [
        'views/report_saledetails_inherit.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
