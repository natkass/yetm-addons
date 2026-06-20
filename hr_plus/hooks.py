from odoo import api, SUPERUSER_ID

def create_input_types(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    input_types = [
        ('OT_REGULAR', 'Regular OT'),
        ('OT_LATE_NIGHT', 'Late Night OT'),
        ('OT_WEEKEND', 'Weekend OT'),
        ('OT_HOLIDAY', 'Holiday OT'),
        ('INCENTIVE', 'Incentive'),
        ('DAILY_ALLOWANCE', 'Daily Allowance'),
        ('DRIVER_INCENTIVE', 'Driver Incentive'),
        ('PENALTY', 'Penalty'),
        ('LOAN', 'Loan'),
    ]
    for code, name in input_types:
        if not env['hr.payslip.input.type'].search([('code', '=', code)], limit=1):
            env['hr.payslip.input.type'].create({'name': name, 'code': code})
