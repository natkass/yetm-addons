# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class FarmerCroppingWind(models.Model):
    _name = 'farmer.cropping.wind'

    name = fields.Char(
        string = 'Wind',
        required= True
    )
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
