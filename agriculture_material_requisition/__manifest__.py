# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Agriculture App with Material Requisition',
    'price': 9.0,
    'version': '6.1.6',
    'category' : 'Inventory/Inventory',
    'currency': 'EUR',
    'license': 'Other proprietary',
    'summary': """This module allow your employees/users to create Material Requisitions for agriculture crop requests.""",
    'description': """ 
Agriculture Material Requisition
Material Requisitions
Material Requisition
manager Requisition
Submit requisition
material Requisition
product Requisitions
material purchase Requisition
material Requisition purchase
purchase material Requisition
product purchase Requisition
Agriculture app
Agriculture Management
Crop Requests
Crops
crop
Agriculture Management Software
Incidents
Dieases Cures
agribusiness
crop yield
agriculture institutes
Farmers
AMS
Farm Locations
farmers
farmer
Agriculture odoo
odoo Agriculture
Agriculture Management System
Animals
print Crop Requests Report
print Crops Report
odoo Agriculture Management Software
Farm Management Software
crop request
cropping
croping

""",
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'http://www.probuse.com',
    'support': 'contact@probuse.com',
    'images': ['static/description/image.png'],
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/agriculture_material_requisition/433',#'https://youtu.be/1tzaqOSofng',
    'depends': [
               'odoo_agriculture',
               'material_purchase_requisitions'
    ],
    'data': [
        'report/material_requisition_report.xml',
        'views/material_purchase_requisition_view.xml',
        'views/menu_item.xml',
        'views/crops_view.xml',
        'views/crop_request_view.xml',
        'views/stock_picking_view.xml',
        'views/purchase_order_view.xml'
    ],
    'installable' : True,
    'application' : False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: