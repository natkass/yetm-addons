from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class HrDailyAllowance(models.Model):
    _name = 'hr.daily.allowance'
    _description = 'Daily Allowance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, readonly=True, default='New')
    manager_id = fields.Many2one('res.users', string='Manager', required=True, tracking=True)
    date_from = fields.Date(string='From', required=True, tracking=True)
    date_to = fields.Date(string='To', required=True, tracking=True)
    remark = fields.Text(string='Remark')
    line_ids = fields.One2many('hr.daily.allowance.line', 'daily_allowance_id', string='Requested For')
    
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    total_allowance_sum = fields.Monetary(string='Overall Allowance', currency_field='currency_id', compute='_compute_total_allowance_sum', store=True)

    def _notify_creator(self, message_body):
        for record in self:
            if record.create_uid and record.create_uid.partner_id:
                record.message_post(
                    body=message_body,
                    partner_ids=[record.create_uid.partner_id.id],
                )

    def _create_activity_for_user(self, user, summary):
        self.env['mail.activity'].create({
            'res_id': self.id,
            'res_model_id': self.env['ir.model']._get_id(self._name),
            'user_id': user.id,
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'summary': summary,
            'date_deadline': fields.Date.today(),
        })

    def _create_activity_for_group(self, group_xmlid, summary, deadline_days=0 ):
            users = self.env.ref(group_xmlid).users
            if not users:
                return
            activities = []
            for user in users:
                activities.append({
                    'res_id': self.id,
                    'res_model_id': self.env['ir.model']._get_id(self._name),
                    'user_id': user.id,
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': summary,
                    'date_deadline': fields.Date.today() + timedelta(days=deadline_days),
                })
            self.env['mail.activity'].create(activities)

    

    def _clear_activities(self):
        self.activity_ids.unlink()

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('hr_verified', 'Verified'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.daily.allowance') or 'New'
        return super().create(vals)

    def action_submit(self):
        for record in self:
            record.write({'state': 'submitted'})
            
            record._create_activity_for_group(
                'hr_plus.group_hr_plus_daily_allowance_verify', 
                'Please verify the daily allowance request',
                
            )

    def action_verify(self):
        for record in self:
            record.write({'state': 'hr_verified'})
            record._clear_activities()
            record._create_activity_for_group(
                'hr_plus.group_hr_plus_daily_allowance_approve', 
                'Please Approve the daily allowance request',                
                
            )


    def action_approve(self):
        self.write({'state': 'approved'})
        self._clear_activities()
        self._notify_creator("Your daily allowance request has been approved.")



    def action_refuse(self):
        self.write({'state': 'refused'})
        self._clear_activities()
        self._notify_creator("Your daily allowance request has been refused.")


    def action_cancel(self):
        self.write({'state': 'cancelled'})
        self._clear_activities()
        self._notify_creator("Your daily allowance request has been cancelled.")


    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        self._clear_activities()

    

    @api.depends('line_ids')
    def _compute_total_allowance_sum(self):
        for record in self:
            total = 0.0
            for line in record.line_ids:
                total += (
                    line.total_allowance
                )
            record.total_allowance_sum = total




class HrDailyAllowanceLine(models.Model):
    _name = 'hr.daily.allowance.line'
    _description = 'Daily allowance Line'

    daily_allowance_id = fields.Many2one('hr.daily.allowance', string='Daily Allowance')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    daily_rate = fields.Float(string='Daily Rate')
    date_count = fields.Float(string='Number of days')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    total_allowance = fields.Monetary(string='Total Allowance', currency_field='currency_id', compute='_compute_total_allowance', store=True)
    remark = fields.Text(string='Remark')
    payslip_id = fields.Many2one('hr.payslip', string='Payslip')
    state = fields.Selection(related='daily_allowance_id.state', string='State', store=True)
    

    @api.onchange('daily_allowance_id')
    def _onchange_daily_allowance_id(self):
        if self.daily_allowance_id:
            used_ids = self.daily_allowance_id.line_ids.mapped('employee_id.id')
            if self.employee_id.id:
                used_ids = [eid for eid in used_ids if eid != self.employee_id.id]
            return {
                'domain': {
                    'employee_id': [('id', 'not in', used_ids)]
                }
            }
        
    @api.depends('daily_rate', 'date_count')
    def _compute_total_allowance(self):
        for record in self:
            record.total_allowance = record.daily_rate * record.date_count




#########################################################################



class HrDriverIncentive(models.Model):
    _name = 'hr.driver.incentive'
    _description = 'Driver Incentive'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, readonly=True, default='New')
    manager_id = fields.Many2one('res.users', string='Manager', required=True, tracking=True)
    date_from = fields.Date(string='From', required=True, tracking=True)
    date_to = fields.Date(string='To', required=True, tracking=True)
    remark = fields.Text(string='Remark')
    line_ids = fields.One2many('hr.driver.incentive.line', 'driver_incentive_id', string='Requested For')
    
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    total_incentive_sum = fields.Monetary(string='Overall Incentive', currency_field='currency_id', compute='_compute_total_incentive_sum', store=True)

    def _notify_creator(self, message_body):
        for record in self:
            if record.create_uid and record.create_uid.partner_id:
                record.message_post(
                    body=message_body,
                    partner_ids=[record.create_uid.partner_id.id],
                )

    def _create_activity_for_user(self, user, summary):
        self.env['mail.activity'].create({
            'res_id': self.id,
            'res_model_id': self.env['ir.model']._get_id(self._name),
            'user_id': user.id,
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'summary': summary,
            'date_deadline': fields.Date.today(),
        })

    def _create_activity_for_group(self, group_xmlid, summary, deadline_days=0 ):
            users = self.env.ref(group_xmlid).users
            if not users:
                return
            activities = []
            for user in users:
                activities.append({
                    'res_id': self.id,
                    'res_model_id': self.env['ir.model']._get_id(self._name),
                    'user_id': user.id,
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': summary,
                    'date_deadline': fields.Date.today() + timedelta(days=deadline_days),
                })
            self.env['mail.activity'].create(activities)

    

    def _clear_activities(self):
        self.activity_ids.unlink()

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('hr_verified', 'Verified'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.driver.incentive') or 'New'
        return super().create(vals)

    def action_submit(self):
        for record in self:
            record.write({'state': 'submitted'})
            
            record._create_activity_for_group(
                'hr_plus.group_hr_plus_driver_incentive_verify', 
                'Please verify the driver incentive request',
                
            )

    def action_verify(self):
        for record in self:
            record.write({'state': 'hr_verified'})
            record._clear_activities()
            record._create_activity_for_group(
                'hr_plus.group_hr_plus_driver_incentive_approve', 
                'Please Approve the driver incentive request',                
                
            )


    def action_approve(self):
        self.write({'state': 'approved'})
        self._clear_activities()
        self._notify_creator("Your driver incentive request has been approved.")



    def action_refuse(self):
        self.write({'state': 'refused'})
        self._clear_activities()
        self._notify_creator("Your driver incentive request has been refused.")


    def action_cancel(self):
        self.write({'state': 'cancelled'})
        self._clear_activities()
        self._notify_creator("Your driver incentive request has been cancelled.")


    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        self._clear_activities()

    

    @api.depends('line_ids')
    def _compute_total_incentive_sum(self):
        for record in self:
            total = 0.0
            for line in record.line_ids:
                total += (
                    line.total_incentive
                )
            record.total_incentive_sum = total


class HrDriverIncentiveLine(models.Model):
    _name = 'hr.driver.incentive.line'
    _description = 'Driver Incentive Line'

    driver_incentive_id = fields.Many2one('hr.driver.incentive', string='Driver Incentive')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    work_performance = fields.Float(string='Work Performance')
    vehicle_self_care = fields.Float(string='Vehicle and Self Care')
    attendance = fields.Float(string='Attendance')
    no_violation = fields.Float(string='No Violation')
    periodic_improvement = fields.Float(string='Periodic Improvement')

    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    total_incentive = fields.Monetary(string='Total incentive', currency_field='currency_id', compute='_compute_total_incentive', store=True)
    remark = fields.Text(string='Remark')
    payslip_id = fields.Many2one('hr.payslip', string='Payslip')
    state = fields.Selection(related='driver_incentive_id.state', string='State', store=True)
    

    @api.onchange('driver_incentive_id')
    def _onchange_driver_incentive_id(self):
        if self.driver_incentive_id:
            used_ids = self.driver_incentive_id.line_ids.mapped('employee_id.id')
            if self.employee_id.id:
                used_ids = [eid for eid in used_ids if eid != self.employee_id.id]
            return {
                'domain': {
                    'employee_id': [('id', 'not in', used_ids)]
                }
            }
        
    @api.depends('work_performance', 'vehicle_self_care', 'attendance', 'no_violation', 'periodic_improvement',)
    def _compute_total_incentive(self):
        for record in self:
            record.total_incentive = record.work_performance + record.vehicle_self_care + record.attendance + record.no_violation + record.periodic_improvement


    