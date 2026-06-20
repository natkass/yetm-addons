# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class FarmerCroppingCloudCover(models.Model):
    _name = 'farmer.cropping.cloudcover'

    name = fields.Char(
        string = 'Cloud Cover',
        required= True
    )
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
