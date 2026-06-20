# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class FarmerLocationCrops(models.Model):
	_name = 'farmer.location.crops'

	name = fields.Char(
		string='Name',
		required=True
	)
	description = fields.Text(
		string='Description'
	)
	
	# start_date = fields.Date(
	# 	string='Start Date',
	# 	required=True
	# )
	# end_date = fields.Date(
	# 	string='End Date',
	# 	required=True
	# )
	crop_period_start = fields.Char(
		string='Crop Period Start',
		required=True
	)
	crop_period_end = fields.Char(
		string='Crop Period End',
		required=True
	)
	crop_task_ids = fields.One2many(
		'crops.tasks.template',
		'crop_id',
		string='Crop Processes'
	)
	crop_material_ids = fields.One2many(
		'crops.materials.job',
		'crop_id',
		domain=[('internal_type','=', 'material')],
		string='Crop Materials'
	)
	crop_labour_ids = fields.One2many(
		'crops.materials.job',
		'crop_id',
		domain=[('internal_type','=', 'labour')],
		string='Crop Labours'
	)
	crop_overhead_ids = fields.One2many(
		'crops.materials.job',
		'crop_id',
		domain=[('internal_type','=', 'overhead')],
		string='Crop Overheads'
	)
	crops_dieases_ids = fields.One2many(
		'crops.dieases',
		'crops_dieases_cures_id',
		string='Crop Dieases'
	)
	warehouse_id = fields.Many2one(
		'stock.warehouse',
		string='Warehouse',
		required=True
	)
	location_id = fields.Many2one(
		'stock.location',
		string='Stock Location',
		required=True
	)
	image = fields.Binary(
        "Image",
        attachment=True
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


