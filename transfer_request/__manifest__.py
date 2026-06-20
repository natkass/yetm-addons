{
    'name': 'Transfer Request',
    'version': '1.1',
    'summary': 'Request Creator for Transfers',
    'description': """ 
            """,
    'depends': ["product", "stock", "mail"],  # Added 'mail' dependency
    'category': 'Extra',
    'sequence': 1,
    'data': [
        'views/menus.xml',
        'security/ir.model.access.csv',
        'sequences/sequences.xml'
    ],
    'test': [],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': True,
    'application': True
}