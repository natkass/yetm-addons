# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Agriculture Integration with Manufacturing (MRP)',
    'price': 99.0,
    'version': '6.2.7',
    'category' : 'Manufacturing/Manufacturing',
    'currency': 'EUR',
    'license': 'Other proprietary',
    'summary': """Agriculture Integration with Manufacturing (MRP) and Bill of Materials.""",
    'description': """
This app allow you to create Manufacturing Order
Agriculture 
Crops
Bills Of Material
Manufacturing
MRP
Process Templates
Crop Requests
Manufacturing Order
Work Order
print Crops Report
print Crop Requests Report
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


""",
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'http://www.probuse.com',
    'support': 'contact@probuse.com',
    'images': ['static/description/image.png'],
    # 'live_test_url': 'https://youtu.be/B1YeWM8P8Vc',
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/agriculture_production_mrp/268',#'https://www.youtube.com/watch?v=6T4X7bEWIzs',
    'depends': [
        'odoo_agriculture',
        'mrp',
        'odoo_agriculture_ecommerce'
    ],
    'data':[
        'security/ir.model.access.csv',
        'report/crop_request_report.xml',
        'report/crops_report.xml',
        'views/crop_views.xml',
        'views/bom_view.xml',
        'views/farmer_cropping_request_view.xml',
        'views/mrp_production_view.xml',
        'views/crops_task_template_view.xml',
    ],
    'installable' : True,
    'application' : False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
