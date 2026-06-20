{
    'name': 'Product Category Sequence',
    'version': '1.0',
    'depends': ['product'],
    'author': 'YourCompany',
    'category': 'Inventory',
    'summary': 'Auto-assign product code based on category sequence',
    'data': [
        'security/product_sequence_groups.xml',
        'data/product_category_sequence.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
}
