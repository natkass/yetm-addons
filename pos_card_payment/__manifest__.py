# -*- coding: utf-8 -*-
{
    'name': 'POS Card Payment',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 777,
    'summary': 'Allow Zoorya Pay Payments in Point of Sale',
    'author': 'Melkam Zeyede',
    'description': """
This module allows you to accept payments by card for SUNMI P3 MIX smart POS deivce through in the Point of Sale (POS).
    """,
    'data': [
        "security/ir.model.access.csv",
        'views/cardpay_report.xml',
    ],
    'depends': ['point_of_sale'],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_card_payment/static/**/*',
        ],
    },
    'license': 'LGPL-3',
}