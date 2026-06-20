{
    "name": "Manufacturing Requests",
    "version": "1.0",
    "category": "Manufacturing",
    "summary": "Track and manage custom manufacturing requests",
    "author": "Your Company",
    "depends": ["sale_management", "mrp", "stock", "mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "reports/manufacturing_request_report.xml",
        "data/ir_sequence_data.xml",
        "reports/report_lifecycle_batch.xml",
        "reports/report_lifecycle_request.xml",

        "views/manufacturing_request_views.xml",
        "views/manufacturing_request_dashboard_views.xml",
        
        "views/manufacturing_request_batch_wizard_views.xml",        
        "views/sale_order_views.xml",
        "views/wizard_views.xml",
        "views/branch_views.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'manufacturing_request\static\src\css\water_mark.css',
        ],
    },
    "installable": True,
    "application": True,
}
