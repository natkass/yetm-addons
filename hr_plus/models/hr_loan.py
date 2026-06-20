from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import timedelta

class HrLoan(models.Model):
    _name = 'hr.loan'
    _description = 'Employee Loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, readonly=True, default='New')
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    type = fields.Selection([
        ('a', 'One-Time Deduction'),
        ('b', 'Installments'),
    ], string="Loan Type", required=True)
    loan_amount = fields.Float(string="Loan Amount", required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    start_date = fields.Date(string="Start Date", required=True)
    months = fields.Integer(string="Duration (Months)", default=1)
    reason = fields.Text(string='Reason')
    # monthly_deduction = fields.Monetary(string="Monthly Deduction", compute='_compute_monthly_deduction', store=True, currency_field='currency_id')
    is_completed = fields.Boolean(string="Completed", default=False, readonly=True)
    payslip_ids = fields.Many2many('hr.payslip', string='Payslips', readonly=True)
    loan_line_ids = fields.One2many('hr.loan.line', 'loan_id', string="Installments")

    paid_amount = fields.Monetary(string="Paid Amount", compute="_compute_amounts", store=True, currency_field='currency_id')
    remaining_amount = fields.Monetary(string="Remaining Amount", compute="_compute_amounts", store=True, currency_field='currency_id')

    is_paid = fields.Boolean(string="Paid", default=False)
    payslip_id = fields.Many2one('hr.payslip', string='Payslip')
    # @api.depends('amount', 'months', 'type')
    # def _compute_monthly_deduction(self):
    #     for rec in self:
    #         rec.monthly_deduction = rec.amount / rec.months if rec.type == 'b' and rec.months else rec.amount

    def action_compute_payments(self):
        for rec in self:
            # if rec.type != 'b' or not rec.start_date or rec.months < 1:
            #     continue

            rec.loan_line_ids.unlink()  # Clear old lines

            amount_per_month = rec.loan_amount / rec.months
            current_date = rec.start_date

            lines = []
            for i in range(rec.months):
                lines.append((0, 0, {
                    'payment_date': current_date,
                    'loan_amount': amount_per_month,
                }))
                current_date += relativedelta(months=1)

            rec.loan_line_ids = lines

    @api.depends('loan_line_ids.loan_amount', 'loan_line_ids.is_paid')
    def _compute_amounts(self):
        for rec in self:
            paid = sum(line.loan_amount for line in rec.loan_line_ids if line.is_paid)
            rec.paid_amount = paid
            rec.remaining_amount = rec.loan_amount - paid

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
        ('approved', 'Finance Approved'),
        ('refused', 'Refused'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.loan') or 'New'
        return super().create(vals)

    def action_submit(self):
        for record in self:
            record.write({'state': 'submitted'})
            
            record._create_activity_for_group(
                'hr_plus.group_hr_plus_loan_verify', 
                'Please verify the employee loan request',
                
            )

    def action_verify(self):
        for record in self:
            record.write({'state': 'hr_verified'})
            record._clear_activities()
            record._create_activity_for_group(
                'hr_plus.group_hr_plus_loan_approve', 
                'Please Approve the employee loan request',                
                
            )


    def action_approve(self):
        self.write({'state': 'approved'})
        self._clear_activities()
        self._notify_creator("Your employee loan request has been approved.")



    def action_refuse(self):
        self.write({'state': 'refused'})
        self._clear_activities()
        self._notify_creator("Your employee loan request has been refused.")


    def action_cancel(self):
        self.write({'state': 'cancelled'})
        self._clear_activities()
        self._notify_creator("Your employee loan request has been cancelled.")


    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        self._clear_activities()

    

class HrLoanLine(models.Model):
    _name = 'hr.loan.line'
    _description = 'Loan Installment Schedule'

    loan_id = fields.Many2one('hr.loan', string="Loan", required=True, ondelete='cascade')
    employee_id = fields.Many2one(related='loan_id.employee_id', string='Employee', readonly=True)
    payment_date = fields.Date(string="Installment Date", required=True)
    loan_amount = fields.Monetary(string="Loan Amount", required=True)
    currency_id = fields.Many2one(related='loan_id.currency_id', readonly=True)
    payslip_id = fields.Many2one('hr.payslip', string='Payslip')
    state = fields.Selection(related='loan_id.state', string='State', store=True)
    type = fields.Selection(related='loan_id.type', string='Loan Type', store=True)
    reason = fields.Text(related='loan_id.reason', string='reason', store=True)    
    is_paid = fields.Boolean(string="Paid", default=False)
