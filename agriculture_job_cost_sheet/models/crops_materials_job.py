# -*- coding: utf-8 -*-
# Part of Probuse Consulting Service Pvt. Ltd. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models  

class CropsMaterialsJob(models.Model):
    
    _inherit = 'crops.materials.job'
    
    job_type_id = fields.Many2one(
        'job.type',
        string='Job Type',
    )
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
