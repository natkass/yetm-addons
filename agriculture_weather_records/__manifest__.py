# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt. Ltd. See LICENSE file for full copyright and licensing details.

{
    'name':'Agriculture Weather Records',
    # 'version':'6.1.2.4',
    'version':'6.1.2',
    'category': 'Services/Project',
    'currency': 'EUR',
        'price': 49.0,

    'license': 'Other proprietary',
    'summary': """This app allow you to record Weathers by day.""",
    'description': """
Agriculture 
Agriculture 
Crops
Crop Requests
Agriculture app
Agriculture Management
Crop Requests
Crops
crop
Agriculture Management Software
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
odoo Agriculture Management Software
Farm Management Software
Weather Forecast
Weather
Weather Records
Print Weather Records Report
            """,
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'http://www.probuse.com',
    'support': 'contact@probuse.com',
    'images': ['static/description/image.png'],
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/agriculture_weather_records/436',#'https://youtu.be/1LKHbXYT2yg',
    'depends': [
        'agriculture_crop_scouting'
    ],
    'data':[
        'data/ir_sequence_data.xml',
        'security/agriculture_weather_security.xml',
        'security/ir.model.access.csv',
        'report/agriculture_weather_report.xml',
        'views/accuweather_view.xml',
        'views/first_eight_hours_view.xml',
        'views/second_eight_hours_view.xml',
        'views/third_eight_hours_view.xml',
        'views/climate_impact_view.xml',
        'views/human_health_view.xml',
        'views/weather_forecast_view.xml'
    ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
