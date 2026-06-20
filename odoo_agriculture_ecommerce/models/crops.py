# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class FarmerLocationCrops(models.Model):
    _inherit = "farmer.location.crops"

    @api.depends('product_temp_id')
    def _compute_is_create_product(self):
        for rec in self:
            if rec.product_temp_id:
                rec.is_create_product = True
            else:
                rec.is_create_product = False

    is_create_product = fields.Boolean(
        string="Is Create Product",
        compute="_compute_is_create_product",
    )
    product_temp_id = fields.Many2one(
        'product.template',
        string="Product"
    )

    # @api.multi #odoo13
    def view_product_temp_request(self):
        action = self.env.ref('sale.product_template_action').sudo().read()[0]
        action['domain'] = [('id','in', self.product_temp_id.ids)]
        return action

    # @api.multi #odoo13
    def action_create_product(self):
        for rec in self:
            vals = {
                'name': rec.name,
                'crop_id': rec.id,
                # 'image_medium': rec.image,
                'image_1920': rec.image,
            }
            product_id = self.env['product.template'].create(vals)
            rec.product_temp_id = product_id.id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:       
