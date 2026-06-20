# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class FarmerCroppingRequest(models.Model):
    _inherit = "farmer.cropping.request"

    # @api.multi #odoo13
    def view_material_requistions(self):
        action = self.env.ref('agriculture_material_requisition.action_material_purchase_requisitions').sudo().read()[0]
        action['domain'] = [('crop_request_id','=', self.id)]
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:       
