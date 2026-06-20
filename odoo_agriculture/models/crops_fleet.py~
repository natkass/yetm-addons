# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class CropsFleet(models.Model):
	_name = 'crops.fleet'
	_rec_name = 'vehicle_id'

	vehicle_id = fields.Many2one(
		'fleet.vehicle',
		string='Vehicle',
		required=True
	)
	crops_tasks_template_id = fields.Many2one(
		'crops.tasks.template',
		string="Crops Tasks Template",
	)
	task_id = fields.Many2one(
		'project.task',
		string="Task"
	)
	start_date = fields.Datetime(
		string='Start Date',
		required=True
	)
	end_date = fields.Datetime(
		string='End Date',
		required=True
	)
	quantity = fields.Float(
		string='Quantity',
		required=True
	)
	description = fields.Text(
		string='Description',
		required=True
	)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


