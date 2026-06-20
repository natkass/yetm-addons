{
    'name': 'Print Order Queue',
    'version': '1.0',
    'summary': 'Queue for print orders to be processed by external print client',
    'author': 'Melkam Zeyede',
    'category': 'Tools',
    'depends': ['base', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/print_order_queue_views.xml',
    ],
    'installable': True,
    'application': False,
}
