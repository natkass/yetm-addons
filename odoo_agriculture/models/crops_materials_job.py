# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class CropsMaterialsJob(models.Model):
    _name = 'crops.materials.job'
    _rec_name = 'internal_type'

    internal_type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('overhead', 'Overhead')],
        string="Type",
        required=True
    )
    crop_id = fields.Many2one(
        'farmer.location.crops',
        string="Crops",
        required=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True
    )
    quantity = fields.Float(
        string='Quantity',
        required=True
    )
    internal_note = fields.Text(
        string='Description',
    )

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.internal_note = self.product_id.name

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: