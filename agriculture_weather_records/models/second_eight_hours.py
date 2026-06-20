# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SecondEightHours(models.Model):
    _name = 'second.eight.hours'

    forecast_id = fields.Many2one(
        'weather.forecast',
        string = 'Forecast'
    )
    second_eight_hour_id = fields.Many2one(
        'farmer.cropping.accuweather',
        string = 'Second Eight Hour',
    )
    col_1 = fields.Char(
        string='9am',
    )
    col_2 = fields.Char(
        string='10am',
    )
    col_3 = fields.Char(
        string='11am',
    )
    col_4 = fields.Char(
        string='12am',
    )
    col_5 = fields.Char(
        string='1pm',
    )
    col_6 = fields.Char(
        string='2pm',
    )
    col_7 = fields.Char(
        string='3pm',
    )
    col_8 = fields.Char(
        string='4pm',
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:       
