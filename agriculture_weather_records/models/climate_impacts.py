# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ClimateImpacts(models.Model):
    _name = 'climate.impacts'

    climate_impact_id = fields.Many2one(
        'farmer.cropping.accuweather',
        string="Climate Impact"
    )
    health_id = fields.Many2one(
        'human.health',
        string="Human Helath",
        required = True
    )
    climate_driver = fields.Char(
        string="Climate Driver",
        required = True
    )
    exposure = fields.Char(
        string="Exposure",
        required = True
    )
    health_outcome = fields.Char(
        string="Health Outcome",
        required = True
    )
    impact = fields.Char(
        string="Impact",
        required = True
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:       
