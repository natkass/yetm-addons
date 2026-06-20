# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class FarmerCroppingRequest(models.Model):
    _inherit = 'farmer.cropping.request'

    crops_soil_id = fields.Many2one(
        'farmer.cropping.soil',
        string="Crops Soil",
        copy=False,
        required=True
    )
    create_date = fields.Datetime(
        "Creation Date", 
        readonly=True, 
        copy=False,
        required=False,
    )
    user_saleperson_id = fields.Many2one(
        'res.users', 
        string='Salesperson', 
        default=lambda self: self.env.user,
        copy=False,
        required=True
    )
    scout_count = fields.Integer(
        compute='_compute_scout_counter',
        string="Scout Count",
    )

    def _compute_scout_counter(self):
        for rec in self:
            rec.scout_count = self.env['farmer.cropping.scoting'].search_count([('custom_crop_request_id', 'in', rec.ids)])

    # @api.multi #odoo13
    def view_scout_request(self):
        action = self.env.ref('agriculture_crop_scouting.action_crops_scoting').sudo().read()[0]
        action['domain'] = [('custom_crop_request_id','in', self.ids)]
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
