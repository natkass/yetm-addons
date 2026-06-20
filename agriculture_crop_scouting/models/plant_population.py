# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class CroppingPlantPopulation(models.Model):
    _name = 'cropping.plantpopulation'

    name = fields.Char(
        string = 'Name',
        required= True
    )
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
