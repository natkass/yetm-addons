# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class FarmerLocationCrops(models.Model):
    _inherit = "farmer.location.crops"

    scout_count = fields.Integer(
        compute='_compute_scout_counter',
        string="Scout Count",
    )

    def _compute_scout_counter(self):
        for rec in self:
            rec.scout_count = self.env['farmer.cropping.scoting'].search_count([('custom_crop_id', 'in', rec.ids)])

    # @api.multi #odoo13
    def view_scout_request(self):
        action = self.env.ref('agriculture_crop_scouting.action_crops_scoting').sudo().read()[0]
        action['domain'] = [('custom_crop_id','in', self.ids)]
        return action
    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:       
