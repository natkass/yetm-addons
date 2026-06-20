from odoo import models, fields, api

class HrContract(models.Model):
    _inherit = 'hr.contract'

    initial_salary_days = fields.Integer(string='Initial Salary Days')

    # @api.model
    # def create(self, vals):
    #     contract = super(HrContract, self).create(vals)
    #     # Reset initial_salary_days to 0 if used (e.g., mid-month join)
    #     if contract.initial_salary_days:
    #         contract._reset_initial_salary_days()
    #     return contract

    # def write(self, vals):
    #     res = super(HrContract, self).write(vals)
    #     # Reset initial_salary_days to 0 after update if used
    #     if 'initial_salary_days' in vals and self.initial_salary_days:
    #         self._reset_initial_salary_days()
    #     return res

    # def _reset_initial_salary_days(self):
    #     """Reset initial_salary_days to 0 and assume 30 days for salary."""
    #     self.write({'initial_salary_days': 0})