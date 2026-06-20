# -*- coding: utf-8 -*-
{
    'name': "POS QR Code telebirrqr",
    'summary': "Telebirr QR Code Payment Integration for Odoo Point of Sale",
    'author': "Melkam Zeyede",
    'category': 'Sales/Point of Sale',
    'version': '0.1',
    'depends': ['base', 'point_of_sale', 'pos_etta'],
    "external_dependencies": {"python": ["pycryptodome"]},
    'data': [
        "security/ir.model.access.csv",
        'views/pos_payment_method_view.xml',
        'views/telebirr_report.xml',
    ],
    "assets": { 
        'point_of_sale._assets_pos': [
            'pos_telebirrqr_qrcode/static/src/app/**/*',
        ]
    }
}