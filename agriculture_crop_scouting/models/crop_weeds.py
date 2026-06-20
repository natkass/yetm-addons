# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class FarmerCroppingWeeds(models.Model):
    _name = 'farmer.cropping.weeds'
    _rec_name = 'weed_id'

    weed_scout_id = fields.Many2one(
        'farmer.cropping.scoting',
        string='Scout',
        required=True,
        copy=False
    )
    weed_id = fields.Many2one(
        'cropping.weeds',
        string='Weed',
        required=True,
    )
    weed_col_1 = fields.Float(
        string='1',
        required=True,
    )
    weed_col_2 = fields.Float(
        string='2',
        required=True,
    )
    weed_col_3 = fields.Float(
        string='3',
        required=True,
    )
    weed_col_4 = fields.Float(
        string='4',
        required=True,
    )
    weed_col_5 = fields.Float(
        string='5',
        required=True,
    )
    description = fields.Char(
        string='Description',
        required=True,
    )
    no_per_square_yard = fields.Char(
        string = 'Number Per Square Yard',
    )
    avg_number = fields.Float(
        string='Average Number',
        required=True,
    )
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
