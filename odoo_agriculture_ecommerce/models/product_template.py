# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    crop_id = fields.Many2one(
        'farmer.location.crops',
        string="Crop",
        readonly= True
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:        
