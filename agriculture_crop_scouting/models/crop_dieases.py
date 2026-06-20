# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class FarmerCroppingDieases(models.Model):
    _name = 'farmer.cropping.dieases'
    _rec_name = 'dieases_id'

    dieases_scout_id = fields.Many2one(
        'farmer.cropping.scoting',
        string='Scout',
        required=True,
        copy=False
    )
    dieases_id = fields.Many2one(
        'cropping.dieases',
        string='Dieases',
        required=True,
    )
    description = fields.Char(
        string='Description',
        required=True,
    )
    dieases_col_1 = fields.Float(
        string='1',
        required=True,
    )
    dieases_col_2 = fields.Float(
        string='2',
        required=True,
    )
    dieases_col_3 = fields.Float(
        string='3',
        required=True,
    )
    dieases_col_4 = fields.Float(
        string='4',
        required=True,
    )
    dieases_col_5 = fields.Float(
        string='5',
        required=True,
    )
    no_of_plant_affected = fields.Char(
        string = 'Number of Plants Affected',
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
