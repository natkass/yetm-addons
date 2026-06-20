from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class HrOvertime(models.Model):
    _name = 'hr.overtime'
    _description = 'Overtime Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, readonly=True, default='New')
    manager_id = fields.Many2one('res.users', string='Manager', required=True, tracking=True)
    date_from = fields.Date(string='From', required=True, tracking=True)
    date_to = fields.Date(string='To', required=True, tracking=True)
    reason = fields.Text(string='Reason')
    line_ids = fields.One2many('hr.overtime.line', 'overtime_id', string='Requested For')
    total_ot_hours = fields.Float(string='Total OT Hours', compute='_compute_total_ot_hours', store=True)
    payslip_count = fields.Integer(string='Payslip Count', compute='_compute_payslip_count')

    dashboard = fields.Char(string='Overtime Summary', required=True, readonly=True, default='Overtime Summary')
    total_record = fields.Integer(compute='_compute_summary_counts', store=False)
    total_submitted = fields.Integer(compute='_compute_summary_counts', store=False)
    total_approved = fields.Integer(compute='_compute_summary_counts', store=False)
    total_refused = fields.Integer(compute='_compute_summary_counts', store=False)

    def _compute_summary_counts(self):
        for record in self:
            # Count records 
            record.total_record = self.env['hr.overtime'].search_count([])
            # Count records in 'submitted' state
            record.total_submitted = self.env['hr.overtime'].search_count([('state', '=', 'submitted')])
            # Count records in 'approved' state
            record.total_approved = self.env['hr.overtime'].search_count([('state', '=', 'approved')])
            # Count records in 'refused' state
            record.total_refused = self.env['hr.overtime'].search_count([('state', '=', 'refused')])

    
    def action_view_overtime_records(self):
        return {
            'name': 'Overtime Records',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.overtime',
            'view_mode': 'tree,form',
            'domain': [],
            'target': 'current',
        }

    def action_view_overtime_submitted(self):
        return {
            'name': 'Submitted Overtime',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.overtime',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'submitted')],
            'target': 'current',
        }

    def action_view_overtime_approved(self):
        return {
            'name': 'Approved Overtime',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.overtime',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'approved')],
            'target': 'current',
        }

    def action_view_overtime_refused(self):
        return {
            'name': 'Refused Overtime',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.overtime',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'refused')],
            'target': 'current',
        }


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
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.overtime') or 'New'
        return super().create(vals)

    def action_submit(self):
        for record in self:
            record.write({'state': 'submitted'})
            
            record._create_activity_for_group(
                'hr_plus.group_hr_plus_overtime_verify', 
                'Please verify the overtime request',
                
            )

    def action_verify(self):
        for record in self:
            record.write({'state': 'hr_verified'})
            record._clear_activities()
            record._create_activity_for_group(
                'hr_plus.group_hr_plus_overtime_approve', 
                'Please Approve the overtime request',                
                
            )


    def action_approve(self):
        self.write({'state': 'approved'})
        self._clear_activities()
        self._notify_creator("Your overtime request has been approved.")



    def action_refuse(self):
        self.write({'state': 'refused'})
        self._clear_activities()
        self._notify_creator("Your overtime request has been refused.")


    # def action_cancel(self):
    #     self.write({'state': 'cancelled'})
    #     for record in self:
    #         record._notify_creator("Your overtime request has been cancelled.")

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        self._clear_activities()
        self._notify_creator("Your overtime request has been cancelled.")


    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
        self._clear_activities()

    

    @api.depends('line_ids')
    def _compute_total_ot_hours(self):
        for record in self:
            total = 0.0
            for line in record.line_ids:
                total += (
                    line.regular_ot +
                    line.late_night_ot +
                    line.weekend_ot +
                    line.holiday_ot
                )
            record.total_ot_hours = total




class HrOvertimeLine(models.Model):
    _name = 'hr.overtime.line'
    _description = 'Overtime Line'

    overtime_id = fields.Many2one('hr.overtime', string='Overtime Request')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    regular_ot = fields.Float(string='Regular OT (Hrs)')
    late_night_ot = fields.Float(string='Late Night OT (Hrs)')
    weekend_ot = fields.Float(string='Weekend OT (Hrs)')
    holiday_ot = fields.Float(string='Holiday OT (Hrs)')
    reason = fields.Text(string='Reason')
    payslip_id = fields.Many2one('hr.payslip', string='Payslip')
    state = fields.Selection(related='overtime_id.state', string='State', store=True)
    

    @api.onchange('overtime_id')
    def _onchange_overtime_id(self):
        if self.overtime_id:
            used_ids = self.overtime_id.line_ids.mapped('employee_id.id')
            if self.employee_id.id:
                used_ids = [eid for eid in used_ids if eid != self.employee_id.id]
            return {
                'domain': {
                    'employee_id': [('id', 'not in', used_ids)]
                }
            }