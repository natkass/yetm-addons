# -*- coding: utf-8 -*-
# Part of Probuse Consulting Service Pvt. Ltd. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError

class FarmerCroppingRequest(models.Model):

    _inherit = 'farmer.cropping.request'

    job_costing_ids = fields.One2many(
        'job.costing',
        'cropping_request_id',
        'Job Costing'
    )
    
    custom_job_costing_count = fields.Integer(
        string='# of Technical',
        compute='_compute_job_costing_count', 
        readonly=True, 
        default=0
    )
    
    
    # @api.multi #odoo13
    def create_job_costing(self):
        for rec in self:
            # if rec.project_id.partner_id:
            if rec.customer_id:
                job_costing = self.env['job.costing']
                job_cost_line = self.env['job.cost.line']
                job_labour_line_ids = self.env['job.cost.line']
                job_costing_vals = {
                                                        'name' : rec.name,
                                                        'project_id': rec.project_id.id,
                                                        # 'partner_id': rec.project_id.partner_id.id,
                                                        'partner_id': rec.customer_id.id,
                                                        'cropping_request_id':rec.id,
                                                        'description':rec.number,
                                                }
                job = job_costing.new(job_costing_vals)
                job._onchange_project_id()
                job_costing_vals = job._convert_to_write({
                name: job[name] for name in job._cache
                })
                job_costing_id = job_costing.create(job_costing_vals)
                for crop_material in rec.crop_ids.crop_material_ids:
                    job_cost_line_vals = {
                                                   'date': fields.Date.today(),
                                                   'product_id': crop_material.product_id.id,
                                                   'job_type' : crop_material.internal_type,
                                                   'job_type_id':crop_material.job_type_id,
                                                   
                                            }
                    job_cost_line = job_cost_line.new(job_cost_line_vals)
                    job_cost_line._onchange_product_id()
                    job_cost_line_vals = job_cost_line._convert_to_write({
                        name: job_cost_line[name] for name in job_cost_line._cache })
                    job_cost_line_vals['product_qty'] = crop_material.quantity
                    job_cost_line_vals['uom_id'] = crop_material.uom_id.id
                    job_costing_id.write({
                        'job_cost_line_ids': [(0, 0, job_cost_line_vals)]
                    })
                for crop_labour in rec.crop_ids.crop_labour_ids:
                    job_labour_line_vals = {
                                                   'date': fields.Date.today(),
                                                   'product_id': crop_labour.product_id.id,
                                                   'job_type' : crop_labour.internal_type,
                                                   'job_type_id':crop_labour.job_type_id,
                                                   'hours': crop_labour.quantity
                                            }
                    job_cost_line = job_cost_line.new(job_labour_line_vals)
                    job_cost_line._onchange_product_id()
                    job_labour_line_vals = job_cost_line._convert_to_write({
                        name: job_cost_line[name] for name in job_cost_line._cache })
                    job_labour_line_vals['product_qty'] = crop_labour.quantity
                    job_labour_line_vals['uom_id'] = crop_labour.uom_id.id
                    
                    job_costing_id.write({
                        'job_labour_line_ids': [(0, 0, job_labour_line_vals)]
                    })
                for crop_overhead in rec.crop_ids.crop_overhead_ids:
                    job_overhead_line_vals = {
                                                   'date': fields.Date.today(),
                                                   'product_id': crop_overhead.product_id.id,
                                                   'job_type' : crop_overhead.internal_type,
                                                   'job_type_id':crop_overhead.job_type_id,
                                            }
                    job_cost_line = job_cost_line.new(job_overhead_line_vals)
                    job_cost_line._onchange_product_id()
                    job_overhead_line_vals = job_cost_line._convert_to_write({
                        name: job_cost_line[name] for name in job_cost_line._cache })
                    job_overhead_line_vals['product_qty'] = crop_overhead.quantity
                    job_overhead_line_vals['uom_id'] = crop_overhead.uom_id.id
                    job_costing_id.write({
                        'job_overhead_line_ids': [(0, 0, job_overhead_line_vals)]
                    })
            
                
                if job_costing_id:                               
                    action = self.env.ref('odoo_job_costing_management.action_job_costing').sudo().read()[0]
                    action['domain'] = [('id', '=', job_costing_id.id)]
                    return action
            else:
                raise UserError(('Please Select Customer.'))
            
                    
    @api.depends()
    def _compute_job_costing_count(self):
        job_costing = self.env['job.costing']
        for record in self:
            # record.custom_job_costing_count = job_costing.search_count([('id', '=', self.job_costing_ids.ids)])
            record.custom_job_costing_count = job_costing.search_count([('id', 'in', self.job_costing_ids.ids)]) #odoo13

            
    # @api.multi #odoo13
    def open_job_costing(self):
        self.ensure_one()
        action = self.env.ref('odoo_job_costing_management.action_job_costing').sudo().read()[0]
        # action['domain'] = [('id', '=', self.job_costing_ids.ids)]
        action['domain'] = [('id', 'in', self.job_costing_ids.ids)] #odoo13
        return action
        
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:        
