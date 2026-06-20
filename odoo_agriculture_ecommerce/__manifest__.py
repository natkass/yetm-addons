# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Ecommerce for Agriculture Crop and Crop Request',
    # 'version': '5.1.2.3',
    'version': '6.1.2',
    'price': 49.0,
    'depends': [
        'odoo_agriculture',
        'website_sale',
        'odoo_agriculture_website'
    ],
    'license': 'Other proprietary',
    # 'category' : 'Sales',
    'category': 'Website/Website',
    'currency': 'EUR',
    'summary': """Ecommerce for Agriculture Crop and Crop Request.""",
    'description': """
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
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/odoo_agriculture_ecommerce/429',#'https://youtu.be/OWf7YiikBrE',
    'data':[
        'views/crop_views.xml',
        'views/product_template_view.xml',
        'views/sale_order_view.xml',
        'views/farmer_cropping_request_view.xml',
        'views/project_task_view.xml'
    ],
    'installable' : True,
    'application' : False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
