# delivery_print_limit/__manifest__.py
{
    "name": "Delivery Print Limit",
    "version": "17.0.1.0",
    "summary": "Limit how many times a Delivery Slip can be printed",
    "author": "Your Company",
    "license": "LGPL-3",
    "depends": ["stock"],
    "data": [
        "views/stock_picking_views.xml"
    ],
    "installable": True,
    "application": False
}
