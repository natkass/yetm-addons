# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
# from odoo.exceptions import UserError, Warning
from odoo.exceptions import UserError


class FarmerCroppingScoting(models.Model):
    _name = 'farmer.cropping.scoting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'custom_crop_id'
    _order = 'id desc'

    state = fields.Selection([
        ('new', 'New'),
        ('confirmed','Confirmed'),
        ('processed', 'Processed'),
        ('done','Done'),
        ('cancel', "Cancelled"),
        ],
        string="Status",
        default='new',
        tracking=True,
        required=True,
        copy=False
    )
    number = fields.Char(
        string='Number',
        readonly=True,
        copy=False
    )
    custom_crop_id = fields.Many2one(
        'farmer.location.crops',
        string='Crop',
        required=True,
        copy=True
    )
    custom_crop_request_id = fields.Many2one(
        'farmer.cropping.request',
        string='Crop Request',
        required=True,
        copy=True
    )
    start_date = fields.Date(
        string='Scouting Start Date',
        required=True,
        copy=True
    )
    end_date = fields.Date(
        string='Scouting End Date',
        required=True,
        copy=True
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id,
        copy=True,
        groups="base.group_multi_company"
    )
    user_id = fields.Many2one(
        'res.users',
        string="Officer",
        default=lambda self: self.env.user,
        required=True,
        copy=True
    )
    process_uid = fields.Many2one(
        'res.users',
        string= 'Processed by',
        copy=True
    )
    processed_date = fields.Date(
        string='Processed Date',
        copy=True
    )
    responsible_user_id = fields.Many2one(
        'res.users',
        string="Responsible User",
        default=lambda self: self.env.user,
        copy=True
    )
    plant_height = fields.Float(
        string='Plant Height',
        required=True,
        copy=True
    )
    soil_temp_id = fields.Many2one(
        'farmer.cropping.soil',
        string= 'Soil Temperature',
        required= True,
        copy=True
    )
    temperature = fields.Float(
        string= 'Temperature',
        required= True,
        copy=True
    )
    temp_uom_id = fields.Many2one(
        'uom.uom',
        'Temperature Unit of Measure',
        required=True,
        copy=True
    )
    soil_condition_id = fields.Many2one(
        'farmer.cropping.weature',
        string="Soil Condition",
        required= True,
        copy=True
    )
    air_temp_id = fields.Many2one(
        'farmer.cropping.air.temperature',
        string="Air Temperature",
        required = True,
        copy=True
    )
    crop_wind_id = fields.Many2one(
        'farmer.cropping.wind',
        string="Wind",
        required = True,
        copy=True
    )
    crop_cloud_cover_id =  fields.Many2one(
        'farmer.cropping.cloudcover',
        string="Cloud Cover",
        required=True,
        copy=True
    )
    internal_note = fields.Text(
        string='Internal Notes',
        copy=True
    )
    crop_insects_ids = fields.One2many(
        'farmer.cropping.insects',
        'insect_scout_id',
        string = 'Insects',
        copy=True
    )
    crop_weeds_ids = fields.One2many(
        'farmer.cropping.weeds',
        'weed_scout_id',
        string='Weeds',
        copy=True
    )
    crop_plant_population_ids = fields.One2many(
        'farmer.cropping.plant.population',
        'plant_population_scout_id',
        string='Plant Population',
        copy=True
    )
    crop_dieases_ids = fields.One2many(
        'farmer.cropping.dieases',
        'dieases_scout_id',
        string = 'Dieases',
        copy=True
    )
    description = fields.Html(
        'Description and Comments:',
        copy=True
    )
    project_id = fields.Many2one(
        'project.project',
        string="Project",
        copy=False
    )
    
    @api.onchange('custom_crop_request_id')
    def onchange_crop_request_id(self):
        for crop in self:
            crop.project_id = crop.custom_crop_request_id.project_id.id

    # @api.multi #odoo13
    def action_new(self):
        return self.write({'state': 'new'})

    # @api.multi #odoo13
    def action_confirmed(self):
        return self.write({'state': 'confirmed'})

    # @api.multi #odoo13
    def action_processed(self):
        return self.write({
            'state': 'processed',
            'process_uid': self.env.user.id,
            'processed_date': fields.Date.today(),
            })

    # @api.multi #odoo13
    def action_done(self):
        return self.write({'state': 'done'})

    # @api.multi #odoo13
    def action_cancel(self):
        return self.write({'state': 'cancel'})

    # @api.multi #odoo13
    def action_reset_to_draft(self):
        return self.write({'state': 'new'})

    # @api.model
    # def create(self, vals):
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['number'] = self.env['ir.sequence'].next_by_code('farmer.cropping.scoting')
        return super(FarmerCroppingScoting,self).create(vals_list)

    # @api.multi #odoo13
    def unlink(self):
        for rec in self:
            if rec.state in ['done','confirmed','processed']:
                raise UserError(_('You can not delete Crop Scouting.'))
        return super(FarmerCroppingScoting, self).unlink()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
