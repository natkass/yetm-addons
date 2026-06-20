from odoo import models
import datetime

class CustomerTaxReport(models.AbstractModel):
    _name = 'report.erca_monthly_tax_report.customer_template'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        date_from = data['form']['date_from']
        date_to = data['form']['date_to']

        # Format setup
        format_header = workbook.add_format({'font_size': 12, 'bold': True, 'bg_color': '#d3dde3', 'bottom': True})
        format_data = workbook.add_format({'font_size': 11, 'num_format': '#,##0.00'})

        # Sheet setup
        sheet = workbook.add_worksheet('Sales Tax Report')
        sheet.write(0, 0, 'ERCA Monthly Sales Tax Report')
        sheet.write(2, 0, 'Date Range:')
        sheet.write(2, 1, f'{date_from} to {date_to}')

        headers = [
            'VAT Category', 'Calendar Type', 'Type of Sales', 'SUPPLIER_TIN', 'INV_DATE', 'MRC',
            'INV_NUM', 'COM_CODE', 'COM_DETAIL', 'DESCRIPTION', 'QUANTITY', 'PRICE',
            'Total Value', 'VAT', 'Value after VAT'
        ]

        for col, header in enumerate(headers):
            sheet.write(6, col, header, format_header)

        # Fetch posted vendor bills within the range
        invoices = self.env['account.move'].sudo().search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to)
        ])

        row = 7
        for invoice in invoices:
            invoice_date = invoice.invoice_date.strftime('%Y-%m-%d')
            for line in invoice.invoice_line_ids:
                vat = sum(tax.amount for tax in line.tax_ids if tax.description == 'VAT')
                vat_2 = (vat / 100) * line.price_subtotal
                after_vat = line.price_subtotal + vat_2

                sheet.write(row, 0, "G", format_data)
                sheet.write(row, 1, "G", format_data)
                sheet.write(row, 2, "1", format_data)
                sheet.write(row, 3, invoice.partner_id.vat or '', format_data)
                sheet.write(row, 4, invoice_date, format_data)
                sheet.write(row, 5, getattr(invoice, 'machine_id', '').name if getattr(invoice, 'machine_id', False) else '', format_data)
                sheet.write(row, 6, "FS-" + invoice.fs_number if getattr(invoice, 'fs_number', False) else invoice.payment_reference or "N/A", format_data)
                sheet.write(row, 7, "78", format_data)
                sheet.write(row, 8, line.product_id.name, format_data)
                sheet.write(row, 9, line.name or '', format_data)
                sheet.write(row, 10, line.quantity, format_data)
                sheet.write(row, 11, line.price_unit, format_data)
                sheet.write(row, 12, line.price_subtotal, format_data)
                sheet.write(row, 13, vat_2, format_data)
                sheet.write(row, 14, after_vat, format_data)

                row += 1

        sheet.set_column('A:O', 15)