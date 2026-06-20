{
    'name': 'MRP Store Request',
    'version': '17.0.1.0.0',
    'summary': 'Create store requests from manufacturing orders via wizard',
    'author': 'THG',
    'license': 'LGPL-3',
    'depends': ['mrp', 'store_request'],
    'data': [
        'security/ir.model.access.csv',
        'views/wizard_store_request_views.xml',
        'views/mrp_production_views.xml',
        'views/transfer_request_views.xml',
    ],
    'installable': True,
    'application': False,
}
