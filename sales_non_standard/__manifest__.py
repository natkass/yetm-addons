# __manifest__.py
{
    'name': 'Non Standard Orders',
    'version': '17.0.1.0.0',
    'summary': 'Used to create a non standard foam',
    'sequence': 15,
    'author': 'Teddy',
    'description': "This module is used to create a non standard foam",
    'category': 'Tools',
    'depends': [
        'sale_management',
        'hr_expense',
        'mrp',
        'account',
        'stock',
        'sale_stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/routes.xml',
        'views/form.xml',
        'views/product.xml',
        'views/mrp_production_view.xml'
        # 'views/menus.xml',  # Uncomment if needed N
    ],
    'assets': {
        'web.assets_backend': [
            'sales_non_standard/static/src/js/demo.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}