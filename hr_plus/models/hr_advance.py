from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta
from odoo.fields import Monetary



class HRAdvanceRequest(models.Model):
    _name = 'hr.advance'
    _description = 'Advance Payment Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    location_id = fields.Selection([
        ('dukam', 'Dukam'),
        ('addis', 'Addis Ababa'),        
    ],required=True,)

    name = fields.Char(string='Reference', required=True, readonly=True, default='New')
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, tracking=True)
    request_date = fields.Date(string="Request Date", default=fields.Date.today, required=True)
    payroll_from = fields.Date(string="Payroll From", required=True)
    payroll_to = fields.Date(string="Payroll To", required=True)
    contract_id = fields.Many2one('hr.contract', string="Contract", compute="_compute_contract", store=True)
    employee_wage = fields.Monetary(string="Employee Wage", compute="_compute_contract", store=True)
    employee_account = fields.Char(string="Bank Account", compute="_compute_contract", store=True)
    penalty_amount = fields.Monetary(string="Current Penalty", compute="_compute_penalty", store=True)
    loan_amount = fields.Monetary(string="Current Loan", compute="_compute_loan", store=True)
    advance_amount = fields.Monetary(string="Requested Amount", required=True)
    payslip_id = fields.Many2one('hr.payslip', string='Payslip')

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    @api.depends('employee_id')
    def _compute_contract(self):
        for rec in self:
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'open')
            ], limit=1)
            rec.contract_id = contract
            rec.employee_wage = contract.wage if contract else 0.0
            rec.employee_account = rec.employee_id.bank_account_id.acc_number if rec.employee_id.bank_account_id else False

    # @api.depends('employee_id')
    # def _compute_account(self):
    #     for rec in self:
    #         contract = self.env['hr.contract'].search([
    #             ('employee_id', '=', rec.employee_id.id),
    #             ('state', '=', 'open')
    #         ], limit=1)
    #         rec.contract_id = contract
    #         rec.employee_wage = contract.wage if contract else 0.0

    @api.depends('employee_id', 'payroll_from', 'payroll_to')
    def _compute_penalty(self):
        for rec in self:
            lines = self.env['hr.penalty.line'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('payment_date', '>=', rec.payroll_from),
                ('payment_date', '<=', rec.payroll_to),
                ('is_paid', '=', False),
            ])
            rec.penalty_amount = sum(lines.mapped('amount'))

    @api.depends('employee_id', 'payroll_from', 'payroll_to')
    def _compute_loan(self):
        for rec in self:
            lines = self.env['hr.loan.line'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('payment_date', '>=', rec.payroll_from),
                ('payment_date', '<=', rec.payroll_to),
                ('is_paid', '=', False),
            ])
            rec.loan_amount = sum(lines.mapped('loan_amount'))


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
        # ('hr_verified', 'HR Verified'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.advance') or 'New'
        return super().create(vals)

    def action_submit(self):
        for record in self:
            record.write({'state': 'submitted'})
            
            record._create_activity_for_group(
                'hr_plus.group_hr_plus_advance_verify', 
                'Please verify the Advance request',
                
            )

    # def action_verify(self):
    #     for record in self:
    #         record.write({'state': 'hr_verified'})
    #         record._clear_activities()
    #         record._create_activity_for_group(
    #             'hr_plus.group_hr_plus_advance_approve', 
    #             'Please Approve the Advance request',                
                
    #         )


    def action_approve(self):
        self.write({'state': 'approved'})
        self._clear_activities()
        self._notify_creator("Your Advance request has been approved.")



    def action_refuse(self):
        self.write({'state': 'refused'})
        self._clear_activities()
        self._notify_creator("Your Advance request has been refused.")



    def action_cancel(self):
        self.write({'state': 'cancelled'})
        self._clear_activities()
        self._notify_creator("Your Advance request has been cancelled.")


    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        self._clear_activities()
