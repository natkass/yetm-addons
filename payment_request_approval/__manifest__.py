# See LICENSE file for full copyright and licensing details.

{
    "name": "Payment Request Approval",
    "version": "17.0.1.0.0",
    "author": "T.A",
    "category": "Tools",
    # "website": "https://github.com/OCA/vertical-hotel",
    "depends": ["sale", "approvals", "account"],  # Make sure these dependencies are compatible with Odoo 17
    # "license": "AGPL-3",
    # "summary": "Hotel Management to Manage Folio and Hotel Configuration",
    # "demo": ["demo/hotel_data.xml"],
    "data": [
        # "security/hotel_security.xml",
        # "security/ir.model.access.csv",
        # "data/sequence.xml",
        # "report/report_view.xml",
        # "report/hotel_folio_report_template.xml",
        # "views/my_views.xml",
        # "views/hotel_room.xml",
        # "views/hotel_room_amenities.xml",
        # "views/hotel_room_type.xml",
        # "views/hotel_service_type.xml",
        # "views/hotel_services.xml",
        # "views/product_product.xml",
        # "views/res_company.xml",
        # "views/actions.xml",
        # "views/menu.xml",
        # "wizard/hotel_wizard.xml",
    ],
    # "css": ["static/src/css/room_kanban.css"],
    # "external_dependencies": {"python": ["dateutil"]},  # Make sure these external dependencies are compatible with Odoo 17
    # "images": ["static/description/Hotel.png"],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 1
}