from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    overtime_line_count = fields.Integer(compute='_compute_overtime_line_count')
    incentive_line_count = fields.Integer(compute='_compute_incentive_line_count')
    daily_allowance_line_count = fields.Integer(compute='_compute_daily_allowance_line_count')
    driver_incentive_line_count = fields.Integer(compute='_compute_driver_incentive_line_count')
    penalty_line_count = fields.Integer(compute='_compute_penalty_line_count')
    loan_line_count = fields.Integer(compute='_compute_loan_line_count')
    advance_count = fields.Integer(compute='_compute_advance_count')

    def _compute_overtime_line_count(self):
        for employee in self:
            employee.overtime_line_count = self.env['hr.overtime.line'].search_count([
                ('employee_id', '=', employee.id)
            ])

    def action_view_overtime_lines(self):
        self.ensure_one()
        return {
            'name': 'Overtime Lines',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.overtime.line',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
        }



    def _compute_incentive_line_count(self):
        for employee in self:
            employee.incentive_line_count = self.env['hr.incentive.line'].search_count([
                ('employee_id', '=', employee.id)
            ])

    def action_view_incentive_lines(self):
        self.ensure_one()
        return {
            'name': 'Incentive Lines',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.incentive.line',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
        }



    def _compute_daily_allowance_line_count(self):
        for employee in self:
            employee.daily_allowance_line_count = self.env['hr.daily.allowance.line'].search_count([
                ('employee_id', '=', employee.id)
            ])

    def action_view_daily_allowance_lines(self):
        self.ensure_one()
        return {
            'name': 'Daily Allowance Lines',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.daily.allowance.line',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
        }
    


    def _compute_driver_incentive_line_count(self):
        for employee in self:
            employee.driver_incentive_line_count = self.env['hr.driver.incentive.line'].search_count([
                ('employee_id', '=', employee.id)
            ])

    def action_view_driver_incentive_lines(self):
        self.ensure_one()
        return {
            'name': 'Driver Incentive Lines',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.driver.incentive.line',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
        }


    def _compute_penalty_line_count(self):
        for employee in self:
            employee.penalty_line_count = self.env['hr.penalty.line'].search_count([
                ('employee_id', '=', employee.id)
            ])

    def action_view_penalty_lines(self):
        self.ensure_one()
        return {
            'name': 'Employee Penalty Lines',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.penalty.line',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
        }
    

    def _compute_loan_line_count(self):
        for employee in self:
            employee.loan_line_count = self.env['hr.loan.line'].search_count([
                ('employee_id', '=', employee.id)
            ])

    def action_view_loan_lines(self):
        self.ensure_one()
        return {
            'name': 'Employee Loan Lines',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.loan.line',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
        }

    def _compute_advance_count(self):
        for employee in self:
            employee.advance_count = self.env['hr.advance'].search_count([
                ('employee_id', '=', employee.id)
            ])

    def action_view_advance(self):
        self.ensure_one()
        return {
            'name': 'Employee Advance',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.advance',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
        }
