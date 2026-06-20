# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class FarmerCroppingWeature(models.Model):
    _name = 'farmer.cropping.weature'

    name = fields.Char(
        string = 'Soil Condition',
        copy=False,
        required=True
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
