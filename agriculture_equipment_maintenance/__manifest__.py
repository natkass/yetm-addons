# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': 'Agriculture with Equipment Maintenance',
    'price': 9.0,
    'version': '6.2.2',
    'category' : 'Manufacturing/Maintenance',
    'currency': 'EUR',
    'license': 'Other proprietary',
    'summary': """Agriculture App with Equipment Maintenance Requests""",
    'description': """ 
Allow Equipment/Maintenance Manager to create a checklist(s)
in Equipment configuration and checklists will be used during Maintenance requests and processes related to agriculture.
Allow you to configure Materials/Items which 
are going to be used in Maintenance Request on Equipment form related to agriculture.
Allow you to configure the checklist(s) 
which will be used in Maintenance requests on the Equipment form related to agriculture.
Checklist(s) and Planned Material(s) on
Maintenance request comes from equipment directly.

""",
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'http://www.probuse.com',
    'support': 'contact@probuse.com',
    'images': ['static/description/image.jpg'],
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/agriculture_equipment_maintenance/67',
    'depends': [
               'odoo_agriculture',
               'asset_mro_maintenance_management'
    ],
    'data': [
            'views/menu_item.xml',
    ],
    'installable' : True,
    'application' : False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

