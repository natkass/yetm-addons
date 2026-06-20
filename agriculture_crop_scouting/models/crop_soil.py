# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class FarmerCroppingSoil(models.Model):
    _name = 'farmer.cropping.soil'

    name = fields.Char(
        string = 'Soil Tempurature',
        copy=False,
        required=True
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
