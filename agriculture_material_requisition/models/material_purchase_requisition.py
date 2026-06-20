# -*- coding: utf-8 -*-
# Part of Probuse Consulting Service Pvt. Ltd. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class MaterialPurchaseRequisition(models.Model):
    _inherit = 'material.purchase.requisition'
    
    crop_id = fields.Many2one(
        'farmer.location.crops',
        string='Crop',
        copy=False
    )
    crop_request_id = fields.Many2one(
        'farmer.cropping.request',
        string='Crop Request',
        copy=False
    )
    agriculture_refrence = fields.Char(
        string="Agriculture Refrence",
        copy=False
    )
    
    @api.onchange('crop_request_id')
    def onchange_crop_request_id(self):
        for crop in self:
            crop.crop_id = crop.crop_request_id.crop_ids.id

    # @api.multi #odoo13
    def request_stock(self):
        res = super(MaterialPurchaseRequisition, self).request_stock()
        stock_obj = self.env['stock.picking'].search([('custom_requisition_id', '=', self.id)])
        purchase_obj = self.env['purchase.order'].search([('custom_requisition_id', '=', self.id)])
        for rec in self:
            stock_vals = {
                    'custom_crop_request_id':rec.crop_request_id.id,
                    'custom_crop_id': rec.crop_id.id,
                    'custom_agriculture_refrence' : rec.agriculture_refrence
                }
            stock_picking = stock_obj.write(stock_vals)
            po_vals = {
                    'custom_crop_request_id':rec.crop_request_id.id,
                    'custom_crop_id': rec.crop_id.id,
                    'custom_agriculture_refrence' : rec.agriculture_refrence
                }
            purchase_order = purchase_obj.write(po_vals)
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
