from odoo import models, fields
import io
import base64
import xlsxwriter


class HrAdvanceReportWizard(models.TransientModel):
    _name = 'hr.advance.report.wizard'
    _description = 'HR Advance Report Wizard'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    location_id = fields.Selection([
        ('dukam', 'Dukam'),
        ('addis', 'Addis Ababa'),
    ], string="Location", required=True)

    file_name = fields.Char(string='File Name', readonly=True)
    file_data = fields.Binary(string='File', readonly=True)

    def action_generate_report(self):
        domain = [
            ('request_date', '>=', self.start_date),
            ('request_date', '<=', self.end_date)
        ]
        if self.location_id:
            domain.append(('location_id', '=', self.location_id))

        advances = self.env['hr.advance'].search(domain)

        # Create a bytes buffer for the Excel file
        output = io.BytesIO()

        # Create a new Excel workbook using xlsxwriter
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Advance Requests")

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9D9D9',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        cell_format = workbook.add_format({'border': 1})
        money_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})

        # Write header
        headers = [
            'Reference',
            'Employee',
            'Bank Account',
            'Amount',
            'Location',
            
            
            
            
            
        ]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Write data rows
        row = 1
        for rec in advances:
            worksheet.write(row, 0, rec.name or '', cell_format)
            worksheet.write(row, 1, rec.employee_id.name or '', cell_format)
            worksheet.write(row, 2, rec.employee_account or '', cell_format)
            
            worksheet.write_number(row, 3, rec.advance_amount or 0.0, money_format)
            worksheet.write(row, 4, rec.location_id or '', cell_format)           
            
            
            row += 1

        # Adjust column width
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:G', 18)
        

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        output.close()

        filename = f"HR_Advance_Report_{self.start_date}_{self.end_date}.xlsx"
        self.write({
            'file_name': filename,
            'file_data': file_data
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model={self._name}&id={self.id}&field=file_data&filename_field=file_name&download=true",
            'target': 'self',
        }
