# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class FarmerCroppingAirTemperature(models.Model):
    _name = 'farmer.cropping.air.temperature'

    name = fields.Char(
        string = 'Air Tempurature',
        required= True
    )
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
