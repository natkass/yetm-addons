# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class ResPartner(models.Model):
	_inherit = "res.partner"

	is_farmer = fields.Boolean(
		string='Is Farmer?',
		copy=True
	)
	is_location = fields.Boolean(
		string='Is Location?',
		copy=True
	)
	is_animal = fields.Boolean(
		string='Is Animal?',
		copy=True
	)
	crop_ids = fields.Many2many(
		'farmer.location.crops',
		string='Crops',
	)
	

	@api.multi
	def get_location_url(self):
		location_action = {
		   'type': 'ir.actions.act_url',
		   'name': "Location",
		   'target': 'new',
		   'url': '/customers/%s' % (self.id)
		   }
		return location_action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
