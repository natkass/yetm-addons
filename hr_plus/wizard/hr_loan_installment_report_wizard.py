from odoo import models, fields, api
import io
import base64
import xlsxwriter


class HrLoanInstallmentReportWizard(models.TransientModel):
    _name = 'hr.loan.installment.report.wizard'
    _description = 'Loan Installment Report Wizard'

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)

    def action_generate_report(self):
        """Generate XLSX report for loan installments within date range."""
        domain = [
            ('payment_date', '>=', self.start_date),
            ('payment_date', '<=', self.end_date),
        ]

        loan_lines = self.env['hr.loan.line'].search(domain, order='payment_date asc')

        # Create Excel workbook in memory
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        sheet = workbook.add_worksheet('Loan Installments')

        # Styles
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})
        money_format = workbook.add_format({'num_format': '#,##0.00'})

        # Header row
        headers = [
            'Loan Reference', 'Employee', 'Installment Date', 'Installment Amount',
            'Paid?', 'Loan Type', 'Reason', 'Loan State'
        ]
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)

        # Data rows
        row = 1
        for line in loan_lines:
            loan = line.loan_id
            sheet.write(row, 0, loan.name or '')
            sheet.write(row, 1, loan.employee_id.name or '')
            sheet.write(row, 2, str(line.payment_date or ''))
            sheet.write_number(row, 3, line.loan_amount or 0.0, money_format)
            sheet.write(row, 4, 'Yes' if line.is_paid else 'No')
            sheet.write(row, 5, dict(loan._fields['type'].selection).get(loan.type, ''))
            sheet.write(row, 6, loan.reason or '')
            sheet.write(row, 7, dict(loan._fields['state'].selection).get(loan.state, ''))
            row += 1

        workbook.close()
        buffer.seek(0)

        # Encode and attach
        file_data = base64.b64encode(buffer.getvalue())
        buffer.close()

        attachment = self.env['ir.attachment'].create({
            'name': 'Loan Installment Report.xlsx',
            'type': 'binary',
            'datas': file_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        download_url = f"/web/content/{attachment.id}?download=true"
        return {
            'type': 'ir.actions.act_url',
            'url': download_url,
            'target': 'self',
        }
