# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class FarmerCroppingRequest(models.Model):
    _name = "farmer.cropping.request"
    _inherit = ['farmer.cropping.request','portal.mixin', 'mail.thread', 'mail.activity.mixin']

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
    )
    phone = fields.Char(
        string='Phone'
    )
    email = fields.Char(
        string='Email'
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
