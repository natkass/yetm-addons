# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class WeatherForecast(models.Model):
    _name = 'weather.forecast'

    name = fields.Char(
        string="Name",
        required=True
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:       
