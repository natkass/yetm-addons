# -*- coding: utf-8 -*-

from odoo import fields, models


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    crop_id = fields.Many2one(
        'farmer.location.crops',
        string="Crop",
        copy = True
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:        
