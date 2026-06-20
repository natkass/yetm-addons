# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class FarmerCroppingPlantPopulation(models.Model):
    _name = 'farmer.cropping.plant.population'
    _rec_name = 'plant_population_id'

    plant_population_scout_id = fields.Many2one(
        'farmer.cropping.scoting',
        string='Scout',
        required=True,
        copy=False
    )
    plant_population_id = fields.Many2one(
        'cropping.plantpopulation',
        string='Plant Population',
        required=True,
    )
    no_of_good_plants = fields.Char(
        string = 'Number of Good Plants',
    )
    description = fields.Char(
        string='Description',
        required=True,
    )
    plant_population_col_1 = fields.Float(
        string='1',
        required=True,
    )
    plant_population_col_2 = fields.Float(
        string='2',
        required=True,
    )
    plant_population_col_3 = fields.Float(
        string='3',
        required=True,
    )
    plant_population_col_4 = fields.Float(
        string='4',
        required=True,
    )
    plant_population_col_5 = fields.Float(
        string='5',
        required=True,
    )
    avg_populations = fields.Float(
        string='Avg. Pop.',
        required=True,
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
