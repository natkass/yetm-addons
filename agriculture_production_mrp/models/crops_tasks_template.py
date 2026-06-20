# -*- coding: utf-8 -*-

from odoo import fields, models


class CropsTasksTemplate(models.Model):
    _inherit = "crops.tasks.template"

    workcenter_id = fields.Many2one(
        'mrp.routing.workcenter',
        string="Work Center Operation",
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:        
