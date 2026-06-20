# -*- coding: utf-8 -*-

from odoo import fields, models, api


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    crop_id = fields.Many2one(
        'farmer.location.crops',
        string="Crop",
        readonly= True,
        copy = False
    )
    custom_request_id = fields.Many2one(
        'farmer.cropping.request',
        string = 'Crop Request',
        copy = False
    )

    # @api.model
    # def create(self, values):
    @api.model_create_multi
    def create(self, vals_list):
        res = super(MrpProduction, self).create(vals_list)
        for values in vals_list:
            if 'custom_request_id' in values:
                custom_request_id = self.env['farmer.cropping.request'].browse(values.get('custom_request_id'))
                custom_request_id.write({
                    'production_id': res.id
                    })
        return res

    @api.onchange('product_id', 'picking_type_id', 'company_id')
    def onchange_custom_product_id(self):
        # res = super(MrpProduction, self).onchange_product_id()
        if self.crop_id and self.crop_id.custom_bom_id:
            self.bom_id = self.crop_id.custom_bom_id.id
            self.product_qty = self.crop_id.manufacturing_quantity
            self.product_uom_id = self.crop_id.manufacturing_uom_id
        # return res 
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:        
