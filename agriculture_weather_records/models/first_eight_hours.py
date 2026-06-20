# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class FirstEightHours(models.Model):
    _name = 'first.eight.hours'

    forecast_id = fields.Many2one(
        'weather.forecast',
        string = 'Forecast'
    )
    first_eight_hour_id = fields.Many2one(
        'farmer.cropping.accuweather',
        string = 'First Eight Hour',
    )
    col_1 = fields.Char(
        string='1am',
    )
    col_2 = fields.Char(
        string='2am',
    )
    col_3 = fields.Char(
        string='3am',
    )
    col_4 = fields.Char(
        string='4am',
    )
    col_5 = fields.Char(
        string='5am',
    )
    col_6 = fields.Char(
        string='6am',
    )
    col_7 = fields.Char(
        string='7am',
    )
    col_8 = fields.Char(
        string='8am',
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:       

