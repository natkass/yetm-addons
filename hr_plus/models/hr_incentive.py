from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta
from odoo.fields import Monetary


class HrInvcentive(models.Model):
    _name = 'hr.incentive'
    _description = 'Incentive Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, readonly=True, default='New')
    manager_id = fields.Many2one('res.users', string='Manager', required=True, tracking=True)
    date_from = fields.Date(string='From', required=True, tracking=True)
    date_to = fields.Date(string='To', required=True, tracking=True)
    reason = fields.Text(string='Reason')
    line_ids = fields.One2many('hr.incentive.line', 'incentive_id', string='Requested For')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    total_incentive = fields.Monetary(string='Total Incentive', currency_field='currency_id', compute='_compute_total_incentive', store=True)


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
        ('hr_verified', 'HR Verified'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.incentive') or 'New'
        return super().create(vals)

    def action_submit(self):
        for record in self:
            record.write({'state': 'submitted'})
            
            record._create_activity_for_group(
                'hr_plus.group_hr_plus_incentive_verify', 
                'Please verify the Incentive request',
                
            )

    def action_verify(self):
        for record in self:
            record.write({'state': 'hr_verified'})
            record._clear_activities()
            record._create_activity_for_group(
                'hr_plus.group_hr_plus_incentive_approve', 
                'Please Approve the Incentive request',                
                
            )


    def action_approve(self):
        self.write({'state': 'approved'})
        self._clear_activities()
        self._notify_creator("Your Incentive request has been approved.")



    def action_refuse(self):
        self.write({'state': 'refused'})
        self._clear_activities()
        self._notify_creator("Your Incentive request has been refused.")



    def action_cancel(self):
        self.write({'state': 'cancelled'})
        self._clear_activities()
        self._notify_creator("Your Incentive request has been cancelled.")


    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        self._clear_activities()

    

    @api.depends('line_ids')
    def _compute_total_incentive(self):
        for record in self:
            total = 0.0
            for line in record.line_ids:
                total += (
                    line.pay_amt
                    
                )
            record.total_incentive = total



class HrIncentiveLine(models.Model):
    _name = 'hr.incentive.line'
    _description = 'Incentive Line'

    incentive_id = fields.Many2one('hr.incentive', string='Incentive Request')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    pay_amt = fields.Monetary(string='Amount', currency_field='currency_id')    
    reason = fields.Text(string='Reason')
    payslip_id = fields.Many2one('hr.payslip', string='Payslip')
    state = fields.Selection(related='incentive_id.state', string='State', store=True)
    

    @api.onchange('incentive_id')
    def _onchange_incentive_id(self):
        if self.incentive_id:
            used_ids = self.incentive_id.line_ids.mapped('employee_id.id')
            if self.employee_id.id:
                used_ids = [eid for eid in used_ids if eid != self.employee_id.id]
            return {
                'domain': {
                    'employee_id': [('id', 'not in', used_ids)]
                }
            }
