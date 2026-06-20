# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ThirdEightHours(models.Model):
    _name = 'third.eight.hours'

    forecast_id = fields.Many2one(
        'weather.forecast',
        string = 'Forecast'
    )
    third_eight_hour_id = fields.Many2one(
        'farmer.cropping.accuweather',
        string = 'Third Eight Hour',
    )
    col_1 = fields.Char(
        string='5pm',
    )
    col_2 = fields.Char(
        string='6pm',
    )
    col_3 = fields.Char(
        string='7pm',
    )
    col_4 = fields.Char(
        string='8pm',
    )
    col_5 = fields.Char(
        string='9pm',
    )
    col_6 = fields.Char(
        string='10pm',
    )
    col_7 = fields.Char(
        string='11pm',
    )
    col_8 = fields.Char(
        string='12pm',
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:       
