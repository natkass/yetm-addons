# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class Task(models.Model):
    _inherit = "project.task"

    product_temp_id = fields.Many2one(
        'product.template',
        string="Product",
        related='custom_request_id.product_temp_id'
    )

class Project(models.Model):
    _inherit = "project.project"

    product_temp_id = fields.Many2one(
        'product.template',
        string="Product",
        related='custom_request_id.product_temp_id'
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

