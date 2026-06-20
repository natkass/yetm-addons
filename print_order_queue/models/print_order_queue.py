from odoo import models, fields, api
import base64
from datetime import datetime

class PrintOrderQueue(models.Model):
    _name = 'print.order.queue'
    _description = 'Print Order Queue'
    _order = 'create_date desc'

    name = fields.Char('Order Name', required=True)
    report_name = fields.Char('Report Name')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('error', 'Error')
    ], default='pending')
    requested_by = fields.Many2one('res.users', string='Requested By', ondelete='set null', default=lambda self: self.env.user)
    report_url = fields.Char('Report URL')
    printer_name = fields.Char('Printer Name')
    error_message = fields.Text('Error Message')
    invoice_id = fields.Many2one('account.move', string='Invoice', ondelete='set null')
    
    # New fields for storing PDF data
    pdf_data = fields.Binary('PDF Data', attachment=True)
    pdf_filename = fields.Char('PDF Filename')
    pdf_size = fields.Integer('PDF Size (bytes)')
    generation_date = fields.Datetime('Generation Date', default=fields.Datetime.now)
    source_url = fields.Char('Source URL', help='The URL used to generate this PDF', default=lambda self: self.env['ir.config_parameter'].sudo().get_param('web.base.url'))
    generation_method = fields.Selection([
        ('xmlrpc', 'XML-RPC'),
        ('http', 'HTTP'),
        ('direct', 'Direct Generation')
    ], string='Generation Method', default='direct')
    
    @api.model
    def create_from_pdf(self, invoice_id, pdf_content, filename, method='direct', url=None):
        """Create a queue entry with PDF data"""
        invoice = self.env['account.move'].browse(invoice_id)
        
        values = {
            'name': f"Invoice {invoice.name or invoice_id}",
            'invoice_id': invoice_id,
            'pdf_data': base64.b64encode(pdf_content).decode() if isinstance(pdf_content, bytes) else pdf_content,
            'pdf_filename': filename,
            'pdf_size': len(pdf_content) if isinstance(pdf_content, bytes) else len(base64.b64decode(pdf_content)),
            'generation_method': method,
            'source_url': url,
            'status': 'done',
            'report_name': 'account.report_invoice',
            'generation_date': datetime.now(),
        }
        
        return self.create(values)
    
    def download_pdf(self):
        """Action to download the PDF using the report URL"""
        self.ensure_one()
        
        # If we have an invoice, use the direct report URL
        if self.invoice_id:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/report/pdf/account.report_invoice/{self.invoice_id.id}',
                'target': 'new',
            }
        
        # Fallback to downloading stored data if no invoice
        if self.pdf_data:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{self._name}/{self.id}/pdf_data/{self.pdf_filename}?download=true',
                'target': 'new',
            }
        
        raise ValueError("No PDF available for download")
    
    def view_invoice_pdf(self):
        """Action to view the invoice PDF directly"""
        self.ensure_one()
        
        if not self.invoice_id:
            raise ValueError("No invoice linked to this record")
        
        # Generate URL for the invoice report
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        pdf_url = f"{base_url}/report/pdf/account.report_invoice/{self.invoice_id.id}"
        
        return {
            'type': 'ir.actions.act_url',
            'url': pdf_url,
            'target': 'new',
        }