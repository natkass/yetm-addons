# -*- coding: utf-8 -*-

from odoo import fields, models

class ProjectTask(models.Model):
    _inherit = 'project.task'

    job_partner_id = fields.Many2one(
        'res.partner',
        string = "Website Customer"
    )
    job_partner_name = fields.Char(
        string = "Website Customer Name"
    )
    job_partner_email = fields.Char(
        string = "Website Customer Email"
    )
    job_partner_phone = fields.Char(
        string = "Website Customer Phone"
    )
    job_category = fields.Selection(
        selection = [
            ('new_request', 'New Request'),
            ('maintenance', 'Maintenance'),
            ('repair', 'Repair'),
            ('technical', 'Technical'),
            ('other', 'Other')
        ],
        string = "Job Order Category",
    )

class ProjectProject(models.Model):
    _inherit = 'project.project'
    
    custom_code = fields.Char(
        string='Code',
        copy=False
    )