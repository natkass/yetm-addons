# -*- coding: utf-8 -*-
# Part of Probuse Consulting Service Pvt. Ltd. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp

class JobCosting(models.Model):

    _inherit = 'job.costing'
    
    cropping_request_id = fields.Many2one(
        'farmer.cropping.request', 
        'Cropping Request',
    )
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:    
    
        
