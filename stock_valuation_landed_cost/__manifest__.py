# -*- coding: utf-8 -*-
{
    'name': 'Stock Valuation Landed Cost',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Track landed cost amounts on stock valuation layers',
    'description': """
        This module adds a landed_cost_amount field to stock valuation layers.
        When a landed cost is distributed, the amount is stored on the original
        valuation layer for easy tracking and reporting.
    """,
    'author': 'Custom',
    'depends': ['stock_landed_costs'],
    'data': [
        'views/stock_valuation_layer_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
