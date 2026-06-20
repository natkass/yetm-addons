# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    custom_crop_id = fields.Many2one(
        'farmer.location.crops',
        string='Crop',
        readonly=True,
        copy=False
    )
    custom_crop_request_id = fields.Many2one(
        'farmer.cropping.request',
        string='Crop Request',
        readonly=True,
        copy=False
    )
    custom_agriculture_refrence = fields.Char(
        string="Agriculture Refrence",
        readonly=True,
        copy=False
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
