# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    # @api.multi #odoo13
    def view_crop_request(self):
        action = self.env.ref('odoo_agriculture.action_farmer_cropping_request').sudo().read()[0]
        crop_ids = self.env['farmer.cropping.request'].search([('sale_id', 'in', self.ids)]).ids
        action['domain'] = [('id','in', crop_ids)]
        return action
    
    # @api.multi #odoo13
    def action_confirm(self):
        for rec in self:
            if any(line.product_id.crop_id for line in rec.order_line):
                for line in rec.order_line:
                    if line.product_id.crop_id:
                        vals = {
                            'crop_ids': line.product_id.crop_id.id,
                            'name': line.product_id.name,
                            'user_id': rec.user_id.id or self.env.user.id,
                            'start_date': fields.Date.today(),
                            'end_date': fields.Date.today(),
                            'sale_id': rec.id,
                            'sale_line_id': line.id,
                            'customer_id': rec.partner_id.id,
                            'phone': rec.partner_id.phone,
                            'email': rec.partner_id.email,
                        }
                        crop_request_id = self.env['farmer.cropping.request'].create(vals)
                        if crop_request_id:
                            line.write({
                                'crop_id': line.product_id.crop_id.id,
                                'crop_request_id': crop_request_id.id,
                            })
        return super(SaleOrder, self).action_confirm()

class SaleOrderline(models.Model):
    _inherit = "sale.order.line"

    crop_id = fields.Many2one(
        'farmer.location.crops',
        string="Crop"
    )
    crop_request_id = fields.Many2one(
        'farmer.cropping.request',
        string="Crop Request"
    )
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
