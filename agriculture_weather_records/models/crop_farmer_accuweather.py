# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class FarmerCroppingaccuweather(models.Model):
    _name = 'farmer.cropping.accuweather'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'location_id'
    _order = 'id desc'

    number = fields.Char(
        string='Number',
        readonly=True,
        copy=False
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.user.company_id,
        copy=False,
        readonly= True
    )
    crop_ids = fields.Many2many(
        'farmer.location.crops',
        string='Crops'
    )
    crop_request_ids = fields.Many2many(
        'farmer.cropping.request',
        string='Crop Requests'
    )
    description = fields.Text(
        string='Description'
    )
    internal_notes = fields.Text(
        string='Internal Notes'
    )
    location_id = fields.Many2one(
        'res.partner',
        'Location',
        required = True,
        copy=True
    )
    min_temp = fields.Float(
        string="Minimum Temperature(in F)",
        required = True,
        copy=True
    )
    max_temp = fields.Float(
        string="Maximum Temperature(in F)",
        required = True,
        copy=True
    )
    day_forcast = fields.Char(
        string="Day Forecast",
        help = """Phrase description of the forecast. 
        (AccuWeather attempts to keep this phrase under 30 characters in length,
        but some languages/weather events may result in 
        a phrase exceeding 30 characters.""",
        required = True,
        copy=True
    )
    epoch_date = fields.Date(
        string="Date",
        required = True,
        copy=True
    )
    first_eight_hour_ids = fields.One2many(
        'first.eight.hours',
        'first_eight_hour_id',
        string = 'First Eight Hours',
    )
    second_eight_hour_ids = fields.One2many(
        'second.eight.hours',
        'second_eight_hour_id',
        string = 'Second Eight Hours',
    )
    third_eight_hour_ids = fields.One2many(
        'third.eight.hours',
        'third_eight_hour_id',
        string = 'Third Eight Hours',
    )
    climate_impact_ids = fields.One2many(
        'climate.impacts',
        'climate_impact_id',
        string = 'Climate impacts'
    )
    tempurature = fields.Float(
        string="Temperature",
    )
    precipitation = fields.Float(
        string="Precipitation",
    )
    day_temperature = fields.Float(
        string="Day Temperature",
    )
    day_precipitation = fields.Float(
        string="Day Precipitation",
    )
    night_tempurature = fields.Float(
        string="Night Temperature",
    )
    night_precipitation = fields.Float(
        string="Night Precipitation",
    )
    internal_note = fields.Text(
        string='Internal Notes'
    )
    day_internal_note = fields.Text(
        string='Day Internal Notes'
    )
    night_internal_note = fields.Text(
        string='Night Internal Notes'
    )
    temp_type = fields.Selection([
            ('high', 'High'),
            ('low', 'Low')],
        string = 'Morning Temp Type'
    )
    morning_tempurature = fields.Float(
        string="Temperature",
    )
    morning_precipitation = fields.Float(
        string="Precipitation",
    )
    morning_internal_note = fields.Text(
        string="Internal Note"
    )
    afternoon_temp_type = fields.Selection([
            ('high', 'High'),
            ('low', 'Low')],
    )
    afternoon_tempurature = fields.Float(
        string="Temperature",
    )
    afternoon_precipitation = fields.Float(
        string="Precipitation",
    )
    afternoon_internal_note = fields.Text(
        string="Internal Note"
    )
    evening_temp_type = fields.Selection([
            ('high', 'High'),
            ('low', 'Low')],
    )
    evening_tempurature = fields.Float(
        string="Temperature",
    )
    evening_precipitation = fields.Float(
        string="Precipitation",
    )
    evening_internal_note = fields.Text(
        string="Internal Note"
    )
    overnight_temp_type = fields.Selection([
            ('high', 'High'),
            ('low', 'Low')],
    )
    overnight_tempurature = fields.Float(
        string="Tempurature",
    )
    overnight_precipitation = fields.Float(
        string="Precipitation",
    )
    overnight_internal_note = fields.Text(
        string="Internal Note"
    )
    

    # @api.model
    # def create(self, vals): 
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['number'] = self.env['ir.sequence'].next_by_code('farmer.cropping.accuweather')
        return super(FarmerCroppingaccuweather,self).create(vals_list)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:       
