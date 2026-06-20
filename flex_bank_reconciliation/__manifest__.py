# -*- coding: utf-8 -*-
{
    'name': "Flex Bank Reconciliation",

    'summary': """ Make a bank reconciliation as QuickBox""",
    'description': """ Make a bank reconciliation as QuickBox""",
    'author': "Flex-OPS - HACHEMI Mohamed Ramzi",
    'license': 'OPL-1',
    'live_test_url': '',
    'website': "https://flex-ops.com",
    'category': 'Accounting/Accounting',
    'version': '17.1',
    'price': 500.0,
    'currency': 'USD',
    'depends': ['base', 'account'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/reconcile_sequence.xml',
        'views/account_account.xml',
        'views/account_move_line.xml',
        'views/settings.xml',
        'views/flex_bank_reconcile.xml',
        'reports/flex_bank_reconcile_report.xml',
        'reports/flex_bank_reconcile_unmatched_report.xml',
        'wizards/reconcile_bank_difference.xml',
    ],
    'images': [
        'static/description/banner.gif',
    ],
    'installable': True,
    'application': False,
}
