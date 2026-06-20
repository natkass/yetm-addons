# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class FarmerCroppingRequest(models.Model):
    _inherit = "farmer.cropping.request"

    sale_id = fields.Many2one(
        'sale.order',
        string="Sale Order"
    )
    sale_line_id = fields.Many2one(
        'sale.order.line',
        string="Sale Order Line"
    )
    product_temp_id = fields.Many2one(
        'product.template',
        string="Product",
        related = 'crop_ids.product_temp_id'
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:        
