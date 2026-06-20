# -*- coding: utf-8 -*-


{
    'name': "Customs Duties and Shipping Fees for Landed Costs",
    "live_test_url": "https://www.odooskillz.com/r/r1V",
    'summary': """
        Customs duties and tariff calculation by HS Code.\n
        Record Shipping fees for import or export taxes.\n
        Precise Odoo inventory valuation for Landed Costs purchase and sales.
        Harmonized system codes, excise duty, import duty, export duty, customs duty, and shipping fees for landed costs.
        Customs VAT calculation.
    """,
    'description': """
 * Automate and simplify your customs fee calculations. 
 * Use standard shipping costs and customs duties and tariffs. 
 * Accurately calculate customs fees of your products' landed costs
 * Streamline your international shipping process and ensure precise product pricing.
""",

    'author': "Odoo Skillz",
    'website': "https://www.odooskillz.com?utm_source=import_fees&utm_medium=App+Store&utm_campaign=App+Store",
    'license': 'OPL-1',

    "images": ["static/description/module.gif"],
    'category': 'Inventory/Purchase',
    'price': 479.0,
    'currency':'USD',
    'version': '17.0.1.1.45',
    'support': 'contact@odooskillz.com',

    # any module necessary for this one to work correctly
    'depends': ['stock_landed_costs'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/harmonized_code_view.xml',
        'views/stock_landed_cost_view.xml',
        'views/account_move_views.xml',
        'views/purchase_order_views.xml',
        'views/product_category.xml',
        'views/product_template.xml',
        'views/res_config_settings_views.xml',
        'views/customs_fees.xml',
        'views/templates.xml',
        'views/menus.xml',
        'views/landed_cost_analysis_report_view.xml',
        'data/init.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'post_init_hook': 'post_init_hook',
}
