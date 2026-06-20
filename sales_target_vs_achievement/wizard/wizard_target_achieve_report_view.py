# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import xlsxwriter
from datetime import date
from dateutil.relativedelta import relativedelta


class WizardTargetAchieveReport(models.TransientModel):
    _name = 'wizard.target.achieve.report'
    _description = 'Franchisee Target vs Achievement (Excel)'

    time_span = fields.Selection(
        [('daily', 'Daily'),
         ('monthly', 'Monthly'),
         ('yearly', 'Yearly')],
        string='Time Span',
        required=True,
        default='monthly',
    )
    selected_date = fields.Date(
        string='Reference Date',
        required=True,
        default=fields.Date.context_today,
    )
    file_data = fields.Binary(string='Excel File', readonly=True)
    file_name = fields.Char(string='Filename', readonly=True)

    # ------------------------------------------------------------------
    # Helper: compute date range exactly like target.achieve
    # ------------------------------------------------------------------
    def _get_date_range(self):
        self.ensure_one()
        today = self.selected_date
        if self.time_span == 'daily':
            return today, today
        elif self.time_span == 'monthly':
            df = today.replace(day=1)
            next_m = df + relativedelta(months=1)
            dt = next_m - relativedelta(days=1)
            return df, dt
        else:  # yearly
            df = today.replace(month=1, day=1)
            dt = today.replace(month=12, day=31)
            return df, dt


    def action_export_excel(self):
        self.ensure_one()
        date_from, date_to = self._get_date_range()
        
        # Fetch confirmed targets in the period
        headers = self.env['target.achieve'].search([
            ('state', '=', 'confirm'),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from),
        ])
        if not headers:
            raise UserError(_('No confirmed targets found for the chosen period.'))

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet('Target vs Achievement')

        # ---------- formats ----------------------------------------------
        bold = wb.add_format({'bold': True, 'bg_color': "#DCE6F1", 'align': 'center', 'valign': 'vcenter'})
        percent = wb.add_format({'num_format': '0.0 "%"', 'align': 'center', 'valign': 'vcenter'})
        money = wb.add_format({'num_format': '#,##0.00', 'align': 'center', 'valign': 'vcenter'})
        merge_format = wb.add_format({'align': 'center', 'valign': 'vcenter'})
        totals_format = wb.add_format({'bold': True, 'bg_color': '#DCE6F1', 'align': 'center', 'valign': 'vcenter'})

        # ---------- header row -------------------------------------------
        headers_titles = ['Time Span', 'Franchisee', 'Target Amount', 'Achieved Amount', 'Achieved %',
                        'Category', 'Category Target', 'Category Achieved', 'Category Achieved %']
        for col, title in enumerate(headers_titles):
            ws.write(0, col, title, bold)

        # ---------- data -------------------------------------------------
        row = 1
        total_target = 0.0
        total_achieved = 0.0

        for head in headers:
            categories = head.line_ids
            if not categories:
                categories = [None]  # Ensure at least one iteration

            start_row = row
            for cat in categories:
                if cat:
                    ws.write(row, 5, cat.category_id.name or '', merge_format)
                    ws.write(row, 6, cat.target_amount or 0.0, money)
                    ws.write(row, 7, cat.achieved_amount or 0.0, money)
                    ws.write(row, 8, cat.achieved_percent or 0.0, percent)
                else:
                    ws.write(row, 5, '', merge_format)
                    ws.write(row, 6, 0.0, money)
                    ws.write(row, 7, 0.0, money)
                    ws.write(row, 8, 0.0, percent)
                row += 1

            end_row = row - 1
            ws.merge_range(start_row, 0, end_row, 0, head.time_span_label or '', merge_format)
            ws.merge_range(start_row, 1, end_row, 1, head.franchisee_id.name or '', merge_format)
            ws.merge_range(start_row, 2, end_row, 2, head.franchisee_target or 0.0, money)
            ws.merge_range(start_row, 3, end_row, 3, head.franchisee_achieved_amt or 0.0, money)
            ws.merge_range(start_row, 4, end_row, 4, head.franchisee_achieved_percent or 0.0, percent)

            # Accumulate totals
            total_target += head.franchisee_target or 0.0
            total_achieved += head.franchisee_achieved_amt or 0.0

        # ---------- totals row -------------------------------------------
        total_row = row + 1
        ws.write(total_row, 1, 'TOTAL', totals_format)
        ws.write(total_row, 2, total_target, money)
        ws.write(total_row, 3, total_achieved, money)
        achieved_percent = (total_achieved / total_target * 100.0) if total_target else 0.0
        ws.write(total_row, 4, achieved_percent, percent)

        # ---------- finish -----------------------------------------------
        ws.autofilter(0, 0, row - 1, len(headers_titles) - 1)
        ws.freeze_panes(1, 0)
        ws.set_column('A:I', 18)

        wb.close()
        output.seek(0)
        self.file_data = base64.b64encode(output.read())
        self.file_name = 'Franchisee_Target_%s.xlsx' % fields.Date.today().strftime('%Y%m%d')
        output.close()

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model={self._name}&id={self.id}&field=file_data&filename_field=file_name&download=true",
            'target': 'self',
        }


        