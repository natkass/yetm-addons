{
    'name': 'Store Request',
    'version': '1.1',
    'summary': 'Request Creator for Transfers',
    'description': """
            """,
    'depends': ["product", "stock", "mail", "purchase_request"],  # Added 'mail' and 'purchase_request' dependency
    'category': 'Localization',
    'sequence': 1,
    'data': [
        'security/ir.model.access.csv',
        'views/menus.xml',
        'views/wizard_confirm_views.xml',
        'sequences/sequences.xml',
        'reports/transfer_request_report.xml',
        'reports/transfer_request_template.xml'
    ],
    'test': [],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': True,
    'application': True
}
