# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class CropsTasksTemplate(models.Model):
    _name = 'crops.tasks.template'
    _rec_name = 'task_id'

    task_id = fields.Many2one(
        'project.task',
        string="Task",
        required=True
    )
    crop_id = fields.Many2one(
        'farmer.location.crops',
        string="Crop",
        required=True
    )
    animal_ids = fields.One2many(
        'crops.animals',
        'crops_tasks_template_id',
        string="Animals",
        required=True
    )
    fleet_ids = fields.One2many(
        'crops.fleet',
        'crops_tasks_template_id',
        string="Fleets",
        required=True
    )
    equipment_ids = fields.Many2many(
        'maintenance.equipment',
        string='Equipments',
        required=True
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


