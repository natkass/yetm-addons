from odoo import models, api

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def _generate_payslips(self):
        res = super()._generate_payslips()
        # inject input for all newly created payslips
        self.slip_ids._inject_inputs()
        return res
    


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def compute_sheet(self):
        res = super().compute_sheet()
        self._inject_inputs()
        return res


    def _inject_inputs(self):
        """Push input values from hr.overtime.line into payslip inputs for each slip in self."""     
              
        code_to_field = {
            'OT_REGULAR': 'regular_ot',
            'OT_LATE_NIGHT': 'late_night_ot',
            'OT_WEEKEND': 'weekend_ot',
            'OT_HOLIDAY': 'holiday_ot',
            'INCENTIVE': 'pay_amt',
            'DAILY_ALLOWANCE': 'total_allowance',
            'DRIVER_INCENTIVE': 'total_incentive',
            'PENALTY': 'amount',
            'LOAN': 'loan_amount',
            'ADVANCE': 'advance_amount',
        }

        
        # Fetch the 4 input types once
        input_types = self.env['hr.payslip.input.type'].search([
            ('code', 'in', list(code_to_field.keys()))
        ])
        code_to_input_type = {ipt.code: ipt.id for ipt in input_types}

        OvertimeLine = self.env['hr.overtime.line']
        IncentiveLine = self.env['hr.incentive.line']
        DailyAllowanceLine = self.env['hr.daily.allowance.line']
        DriverIncentiveLine = self.env['hr.driver.incentive.line']
        PenaltyLine = self.env['hr.penalty.line']
        LoanLine = self.env['hr.loan.line']
        Advance = self.env['hr.advance']
        

        for payslip in self:
            run = payslip.payslip_run_id
            if not (run and run.date_start and run.date_end):
                continue

            # get all OT lines for this employee in the batch period
            ot_lines = OvertimeLine.search([
                ('employee_id', '=', payslip.employee_id.id),
                ('overtime_id.state', '=', 'approved'),
                ('overtime_id.date_to', '>=', run.date_start),
                ('overtime_id.date_to', '<=', run.date_end),
                ('payslip_id', '=', False),
            ])

            in_lines = IncentiveLine.search([
                ('employee_id', '=', payslip.employee_id.id),
                ('incentive_id.state', '=', 'approved'),
                ('incentive_id.date_to', '>=', run.date_start),
                ('incentive_id.date_to', '<=', run.date_end),
                ('payslip_id', '=', False),
            ])

            da_lines = DailyAllowanceLine.search([
                ('employee_id', '=', payslip.employee_id.id),
                ('daily_allowance_id.state', '=', 'approved'),
                ('daily_allowance_id.date_to', '>=', run.date_start),
                ('daily_allowance_id.date_to', '<=', run.date_end),
                ('payslip_id', '=', False),
            ])


            di_lines = DriverIncentiveLine.search([
                ('employee_id', '=', payslip.employee_id.id),
                ('driver_incentive_id.state', '=', 'approved'),
                ('driver_incentive_id.date_to', '>=', run.date_start),
                ('driver_incentive_id.date_to', '<=', run.date_end),
                ('payslip_id', '=', False),
            ])
            

            pn_lines = PenaltyLine.search([
                ('employee_id', '=', payslip.employee_id.id),
                ('penalty_id.state', '=', 'approved'),
                ('payment_date', '>=', run.date_start),
                ('payment_date', '<=', run.date_end),
                ('payslip_id', '=', False),
                ('is_paid', '=', False),                
            ])

            lo_lines = LoanLine.search([
                ('employee_id', '=', payslip.employee_id.id),
                ('loan_id.state', '=', 'approved'),
                ('payment_date', '>=', run.date_start),
                ('payment_date', '<=', run.date_end),
                ('payslip_id', '=', False),
                ('is_paid', '=', False),                
            ])

            ad_lines = Advance.search([
                ('employee_id', '=', payslip.employee_id.id),
                ('state', '=', 'hr_verified'),
                ('request_date', '>=', run.date_start),
                ('request_date', '<=', run.date_end),
                ('payslip_id', '=', False),
                         
            ])

            # pn_lines = PenaltyLine.search([
            #     ('employee_id', '=', payslip.employee_id.id),
            #     ('penalty_id.state', '=', 'approved'),
            #     ('payslip_id', '=', False),
            #     ('is_paid', '=', False),
            #     '|',  # OR logic
            #         '&',  # For Type A (one-time)
            #             ('penalty_id.type', '=', 'a'),
            #             ('penalty_id.start_date', '>=', run.date_start),
            #             ('penalty_id.start_date', '<=', run.date_end),
            #         '&',  # For Type B (installments)
            #             ('penalty_id.type', '=', 'b'),
            #             ('payment_date', '>=', run.date_start),
            #             ('payment_date', '<=', run.date_end),
            # ])


            # sum per code
            totals = {code: 0.0 for code in code_to_field}
            for l in ot_lines:
                for code, field in code_to_field.items():
                    totals[code] += getattr(l, field, 0.0)

            for l in in_lines:
                totals['INCENTIVE'] += l.pay_amt or 0.0

            for l in da_lines:
                totals['DAILY_ALLOWANCE'] += l.total_allowance or 0.0

            for l in di_lines:
                totals['DRIVER_INCENTIVE'] += l.total_incentive or 0.0

            for l in pn_lines:
                totals['PENALTY'] += l.amount or 0.0

            for l in lo_lines:
                totals['LOAN'] += l.loan_amount or 0.0

            for l in ad_lines:
                totals['ADVANCE'] += l.advance_amount or 0.0


            # insert inputs
            for code, amount in totals.items():
                if not amount:
                    continue
                input_type_id = code_to_input_type.get(code)
                if not input_type_id:
                    # no matching input type defined -> skip
                    continue

                existing = payslip.input_line_ids.filtered_domain([('code', '=', code)])
                if existing:
                    existing.amount = amount
                else:
                    self.env['hr.payslip.input'].create({
                        'payslip_id': payslip.id,
                        'input_type_id': input_type_id,
                        'code': code,
                        'amount': amount,
                        'name': code.replace('OT_', '').replace('_', ' ').title(),
                    })

            # mark lines as used
            ot_lines.write({'payslip_id': payslip.id})
            in_lines.write({'payslip_id': payslip.id})
            da_lines.write({'payslip_id': payslip.id})
            di_lines.write({'payslip_id': payslip.id})
            pn_lines.write({'payslip_id': payslip.id,'is_paid': True, })
            lo_lines.write({'payslip_id': payslip.id,'is_paid': True, })
            ad_lines.write({'payslip_id': payslip.id})
            
    
    
    def _reset_linked_lines(self):
        OvertimeLine = self.env['hr.overtime.line']
        IncentiveLine = self.env['hr.incentive.line']
        DailyAllowanceLine = self.env['hr.daily.allowance.line']
        DriverIncentiveLine = self.env['hr.driver.incentive.line']
        PenaltyLine = self.env['hr.penalty.line']
        LoanLine = self.env['hr.loan.line']
        Advance = self.env['hr.advance']
        for payslip in self:
            OvertimeLine.search([('payslip_id', '=', payslip.id)]).write({'payslip_id': False})
            IncentiveLine.search([('payslip_id', '=', payslip.id)]).write({'payslip_id': False})
            DailyAllowanceLine.search([('payslip_id', '=', payslip.id)]).write({'payslip_id': False})
            DriverIncentiveLine.search([('payslip_id', '=', payslip.id)]).write({'payslip_id': False})
            PenaltyLine.search([('payslip_id', '=', payslip.id)]).write({'payslip_id': False ,'is_paid': False})
            LoanLine.search([('payslip_id', '=', payslip.id)]).write({'payslip_id': False,'is_paid': False })
            Advance.search([('payslip_id', '=', payslip.id)]).write({'payslip_id': False})

    def unlink(self):
        self._reset_linked_lines()
        return super().unlink()

    def action_payslip_draft(self):
        self._reset_linked_lines()
        return super().action_payslip_draft()