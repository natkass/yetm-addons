# -*- coding: utf-8 -*-
from odoo import models, api
import base64
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def get_invoice_pdf_via_render_qweb(self, invoice_ids, base_url=None):
        """Generate PDF for invoice using the same report as the working URL"""
        if isinstance(invoice_ids, int):
            invoice_ids = [invoice_ids]
        
        invoice = self.browse(invoice_ids[0]).sudo()
        if not invoice.exists():
            raise ValueError(f"Invoice with ID {invoice_ids[0]} not found")
        
        try:
            # Dynamically set the base URL if provided
            if base_url:
                # Get the system parameter
                IrConfigParameter = self.env['ir.config_parameter'].sudo()
                
                # Store the current base URL
                current_base_url = IrConfigParameter.get_param('web.base.url')
                
                # Temporarily set the new base URL
                IrConfigParameter.set_param('web.base.url', base_url)
                _logger.info(f"Temporarily set web.base.url to: {base_url}")
            
            # Use the standard Odoo method to generate invoice PDF
            # This is the most compatible approach
            report_name = 'account.report_invoice'
            
            # Try to generate the PDF using the standard method
            try:
                pdf_content, _ = self.env['ir.actions.report'].sudo()._render(
                    report_name,
                    invoice.ids,
                    data={'report_type': 'pdf'}
                )
            except:
                # Fallback to alternative report names
                try:
                    pdf_content, _ = self.env['ir.actions.report'].sudo()._render(
                        'account.account_invoices',
                        invoice.ids,
                        data={'report_type': 'pdf'}
                    )
                except:
                    # Last fallback
                    pdf_content, _ = self.env['ir.actions.report'].sudo()._render(
                        'account.report_invoice_with_payments',
                        invoice.ids,
                        data={'report_type': 'pdf'}
                    )
            
            filename = invoice._get_report_base_filename()
            
            # Store the PDF in the print queue
            try:
                queue_entry = self.env['print.order.queue'].create_from_pdf(
                    invoice_id=invoice.id,
                    pdf_content=pdf_content,
                    filename=f"{filename}.pdf",
                    method='xmlrpc' if base_url else 'direct',
                    url=base_url
                )
                _logger.info(f"PDF stored in print queue with ID: {queue_entry.id}")
            except Exception as e:
                _logger.warning(f"Failed to store PDF in print queue: {str(e)}")
            
            # Restore the original base URL if it was changed
            if base_url and 'current_base_url' in locals():
                IrConfigParameter.set_param('web.base.url', current_base_url)
                _logger.info(f"Restored web.base.url to: {current_base_url}")
            
            return base64.b64encode(pdf_content).decode(), f"{filename}.pdf"
            
        except Exception as e:
            _logger.error(f"PDF generation failed for invoice {invoice_ids[0]}: {str(e)}")
            
            # Restore the original base URL in case of error
            if base_url and 'current_base_url' in locals():
                IrConfigParameter = self.env['ir.config_parameter'].sudo()
                IrConfigParameter.set_param('web.base.url', current_base_url)
                _logger.info(f"Restored web.base.url to: {current_base_url} (after error)")
            
            raise
