# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class FarmerLocationCrops(models.Model):
    _inherit = "farmer.location.crops"

    # @api.multi #odoo13
    def view_material_requistions(self):
        action = self.env.ref('agriculture_material_requisition.action_material_purchase_requisitions').sudo().read()[0]
        action['domain'] = [('crop_id','=', self.id)]
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:       
