# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class FarmerCroppingInsects(models.Model):
    _name = 'farmer.cropping.insects'
    _rec_name = 'insect_id'

    insect_scout_id = fields.Many2one(
        'farmer.cropping.scoting',
        string='Scout',
        required=True,
        copy=False
    )
    insect_id = fields.Many2one(
        'cropping.insects',
        string='Insect',
        required=True,
    )
    causing_damage = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ],
        string='Is it Causing Damage?',
        required=True,
    )
    insect_col_1 = fields.Float(
        string='1',
        required=True,
        copy=False
    )
    insect_col_2 = fields.Float(
        string='2',
        required=True,
    )
    insect_col_3 = fields.Float(
        string='3',
        required=True,
    )
    insect_col_4 = fields.Float(
        string='4',
        required=True,
    )
    insect_col_5 = fields.Float(
        string='5',
        required=True,
    )
    no_of_area_scouted = fields.Char(
        string = 'Number Per Area Scouted',
    )
    description = fields.Char(
        string='Description',
        required=True,
    )
    total = fields.Float(
        string='Total',
        required=True,
    )
    percentage = fields.Float(
        string='Percentage(%)',
        required=True,
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
