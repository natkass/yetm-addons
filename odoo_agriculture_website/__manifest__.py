# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Agriculture Crop Request from Website by Customer',
    'price': 49.0,
    # 'version': '7.1.2.5',
    'version': '8.1.2',
    'category': 'Website/Website',
    'depends': [
        'odoo_agriculture'
    ],
    'currency': 'EUR',
    'license': 'Other proprietary',
    'summary': "This app allow your customer / farmer / consumer to create crop request from website page and show crop request in my account portal.",
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
crop request
cropping
croping
This app allow create a crop request in backend side

     """,
    'author': "Probuse Consulting Service Pvt. Ltd.",
    'website': "http://www.probuse.com",
    'support': 'contact@probuse.com',
    'images': ['static/description/image.png'],
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/odoo_agriculture_website/424',#'https://youtu.be/v8AvL6StwBg',
    'data':[
       'views/crop_request_view.xml',
       'views/portal_form_view.xml',
       'views/crop_request_account_view.xml',
    ],
    'installable' : True,
    'application' : False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
