# -*- coding: utf-8 -*-
{
    'name': 'Stock Valuation Report',
    'version': '17.0.2.0.0',
    'category': 'Inventory',
    'summary': 'Generate stock valuation reports and movement analysis',
    'description': """
        Stock Valuation Report
        ================================

        Features:
        - Generate stock valuation snapshot as of any end date
        - Average cost calculation including landed costs
        - UoM-aware quantity conversions
        - Filter by product code/name
        - Filter by specific locations
        - Export to Excel format
        - Landed-cost SVLs dated by account_move.date
        - Regular SVLs use create_date
        - Internal locations only

        Stock Movement Valuation:
        - View all stock movements (Sales, Purchases, Internal Transfers, Manufacturing, Adjustments)
        - See cost/value for each movement
        - Running balance per product and location
        - Date range filtering (start date and end date)
        - Location-specific analysis
        - Excel export with full details
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['stock', 'stock_account', 'stock_valuation_landed_cost'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/stock_snapshot_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
