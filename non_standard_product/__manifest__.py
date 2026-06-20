# __manifest__.py
{
    "name": "Non-Standard Product Configurator",
    "version": "17.0.1.0.0",
    "summary": "Configure Non-Standard Products with dynamic pricing and BoM generation",
    "description": """
Non-Standard Product Configurator
=================================
This module allows users to:
 - Define custom parameters (Foam, Fabric, Shape, Fasha, Seal, Glue, Tape Edge)
 - Configure Non-Standard products from Sales Orders
 - Dynamically calculate sales price based on length, width, height, and selected parameters
 - Automatically generate Products and Bills of Materials (BoMs)
 - Add configured product directly to the Sales Order line
 - Track products with a unique sequence (NSPxxxx)
    """,
    "author": "Your Company",
    "website": "https://www.yourcompany.com",
    "license": "LGPL-3",
    "category": "Sales/Manufacturing",
    "depends": [ 'sale', 'product', 'mrp'],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        
        "views/non_standard_parameter_views.xml",
        "views/sale_order_views.xml",
        "views/product_views.xml",
        "views/non_standard_wizard_views.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'non_standard_product/static/src/css/custom_styles.css',
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
