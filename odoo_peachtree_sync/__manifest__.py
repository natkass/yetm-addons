{
    "name": "Odoo to Peachtree Sales Sync",
    "version": "17.0.2.0.0",
    "summary": "Export Odoo sales invoices as CSV for Peachtree 2010 import",
    "category": "Accounting",
    "author": "ETTA",
    "depends": ["account", "sale", "product", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/peachtree_export_wizard_views.xml",
        "wizard/peachtree_customer_product_export_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
