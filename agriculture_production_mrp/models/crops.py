# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class FarmerLocationCrops(models.Model):
    _inherit = "farmer.location.crops"

    is_create_bom = fields.Boolean(
        string="Is Create Bom",
        compute="_compute_is_create_bom",
    )
    custom_bom_id = fields.Many2one(
        'mrp.bom',
        string="Bills of Material",
        readonly=True ,
        copy = False
    )   
    # routing_id = fields.Many2one(
    #     'mrp.routing',
    #     string= 'Routing',
    #     related= 'custom_bom_id.routing_id',
    #     readonly=True,
    #     store=True,
    #     copy = False
    # )
    manufacturing_quantity = fields.Float(
        string= 'Manufacturing Qty'
    )
    manufacturing_uom_id = fields.Many2one(
        'uom.uom',
        string = 'Manufacturing UoM'
    )

    @api.depends('custom_bom_id')
    def _compute_is_create_bom(self):
        for rec in self:
            if rec.custom_bom_id:
                rec.is_create_bom = True
            else:
                rec.is_create_bom = False
    
    # @api.multi #odoo13
    def view_bom_request(self):
        action = self.env.ref('mrp.mrp_bom_form_action').sudo().read()[0]
        action['domain'] = [('id','in', self.custom_bom_id.ids)]
        return action

    
    # @api.multi #odoo13
    def action_create_bom(self):
        bom = self.env['mrp.bom']
        bom_line = self.env['mrp.bom.line']
        bom_material_line_ids = self.env['mrp.bom.line']
        for rec in self:
            if rec.product_temp_id:
                bom_vals = {
                    'product_tmpl_id': rec.product_temp_id.id,
                    'crop_id': rec.id,
                    'product_qty': rec.manufacturing_quantity,
                    'product_uom_id': rec.manufacturing_uom_id.id
                }
                boms = bom.new(bom_vals)
                boms.onchange_product_tmpl_id()
                bom_vals = boms._convert_to_write({
                        name: boms[name] for name in boms._cache
                })
                bom_id = bom.sudo().create(bom_vals)
                rec.custom_bom_id = bom_id.id
                for crop_material in rec.crop_material_ids:
                    bom_line_vals = {   
                        'product_id' : crop_material.product_id.id,
                        'product_qty': crop_material.quantity,
                        'product_uom_id' : crop_material.uom_id.id,
                        'bom_id': bom_id.id,
                    }
                    bom_line = bom_line.new(bom_line_vals)
                    bom_line.onchange_product_id()
                    bom_line_vals = bom_line._convert_to_write({
                        name: bom_line[name] for name in bom_line._cache })
                    bom_id.write({
                        'bom_line_ids': [(0, 0, bom_line_vals)]
                    })
                action = self.env.ref('mrp.mrp_bom_form_action')
                result = action.sudo().read()[0]
                result['domain'] = [('id', '=', bom_id.id)]
                return result
            else:
                raise UserError(('You can not create Bom before creation of Product.'))


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:       
