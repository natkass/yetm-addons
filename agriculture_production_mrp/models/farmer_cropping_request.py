# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class FarmerCroppingRequest(models.Model):
    _inherit = "farmer.cropping.request"

    production_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order',
        copy = False,
        readonly = True
        )
    manufacturing_quantity = fields.Float(
        string= 'Manufacturing Qty'
    )
    manufacturing_uom_id = fields.Many2one(
        'uom.uom',
        string = 'Manufacturing UoM'
    )
    custom_bom_id = fields.Many2one(
        'mrp.bom',
        string="Bills of Material",
        copy = False
    )   
    # routing_id = fields.Many2one(
    #   'mrp.routing',
    #   string= 'Routing',
    #   copy = False
    # )


    @api.onchange('crop_ids')
    def onchange_crop_id(self):
        for crop in self:
            if crop.crop_ids:
                crop.manufacturing_quantity = crop.crop_ids.manufacturing_quantity
                crop.manufacturing_uom_id = crop.crop_ids.manufacturing_uom_id.id
                crop.custom_bom_id = crop.crop_ids.custom_bom_id.id
                # crop.routing_id = crop.crop_ids.routing_id.id


    # @api.multi #odoo13
    def view_mrp_request(self):
        action = self.env.ref('mrp.mrp_production_action').sudo().read()[0]
        action['domain'] = [('id', 'in', self.production_id.ids)]
        return action
    
    # @api.multi #odoo13
    # def action_create_mrp(self):
    #   production_obj = self.env['mrp.production']
    #   company_obj = self.env['res.company']   
    #   for rec in self:
    #       mrp_vals = {
    #           'product_id': rec.product_temp_id.product_variant_id.id,
    #           'product_qty': 1,
    #           'product_uom_id': rec.product_temp_id.uom_id.id,
    #           'bom_id': rec.custom_bom_id.id,
    #           'crop_id': rec.crop_ids.id,
    #           'custom_request_id': rec.id,
    #           'origin': rec.number
    #           }
    #       picking_type_id = production_obj._get_default_picking_type()
    #       company_id = company_obj._company_default_get()
    #       mrp_vals.update({
    #           'picking_type_id': picking_type_id,
    #           'company_id': company_id,
    #           })
    #       mrps = production_obj.new(mrp_vals)
    #       mrps.onchange_product_id()
    #       mrps._onchange_bom_id()
    #       mrps.onchange_picking_type()
    #       mrp_vals = mrps._convert_to_write({
    #               name: mrps[name] for name in mrps._cache
    #       })
    #       mrp_vals['product_qty'] = rec.manufacturing_quantity
    #       mrp_vals['product_uom_id'] = rec.manufacturing_uom_id.id
    #       if not rec.custom_bom_id:
    #           raise UserError(('Please select Bills of Material On Crop'))
    #       if not rec.manufacturing_quantity:
    #           raise UserError(('Please select Manufacturing Qty On Crop'))
    #       if not rec.manufacturing_uom_id:
    #           raise UserError(('Please select Manufacturing UoM On Crop'))
    #       if rec.custom_bom_id.product_qty <= 0:
    #           raise UserError(('Quantity of Selected BOM must be positive!'))
    #       mrp_id = production_obj.sudo().create(mrp_vals)
    #       rec.production_id = mrp_id
    #       action = self.env.ref('mrp.mrp_production_action')
    #       result = action.sudo().read()[0]
    #       result['domain'] = [('id', '=', mrp_id.id)]
    #       return result

    def action_create_mrp(self):
        # if not rec.custom_bom_id:
        #       raise UserError(('Please select Bills of Material On Crop'))
        # if not rec.manufacturing_quantity:
        #       raise UserError(('Please select Manufacturing Qty On Crop'))
        # if not rec.manufacturing_uom_id:
        #       raise UserError(('Please select Manufacturing UoM On Crop'))
        # if rec.custom_bom_id.product_qty <= 0:
        #       raise UserError(('Quantity of Selected BOM must be positive!'))
        if not self.custom_bom_id:
              raise UserError(('Please select Bills of Material On Crop'))
        if not self.manufacturing_quantity:
              raise UserError(('Please select Manufacturing Qty On Crop'))
        if not self.manufacturing_uom_id:
              raise UserError(('Please select Manufacturing UoM On Crop'))
        if self.custom_bom_id.product_qty <= 0:
              raise UserError(('Quantity of Selected BOM must be positive!'))
        for rec in self:
            action = self.env.ref('mrp.mrp_production_action').sudo().read()[0]
            action['views'] = [(self.env.ref('mrp.mrp_production_form_view').id, 'form')]
            action['context'] = {
                'default_product_id': rec.product_temp_id.product_variant_id.id,
                'default_product_qty': 1,
                'default_product_uom_id': rec.product_temp_id.uom_id.id,
                'default_bom_id': rec.custom_bom_id.id,
                'default_crop_id': rec.crop_ids.id,
                'default_custom_request_id': rec.id,
                'default_origin': rec.number
            }
            return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:       
