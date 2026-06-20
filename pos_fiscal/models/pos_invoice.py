from odoo import models, fields, api
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)

class PosInvoice(models.Model):
    _name = 'pos.invoice'
    _description = 'POS Invoice'

    fsNumber = fields.Integer(string='FS Number', index=True)
    referenceNumber = fields.Char(string='Reference Number')
    paymentType = fields.Char(string='Payment Type')
    paymentReferenceNumber = fields.Char(string='Payment Reference Number')

    buyerName = fields.Char(string='Buyer Name')
    buyerTradeName = fields.Char(string='Buyer Trade Name')
    buyerTaxIdNumber = fields.Char(string='Buyer Tax ID')
    buyerPhoneNumber = fields.Char(string='Buyer Phone Number')

    cashierName = fields.Char(string='Cashier Name')
    headerMemo = fields.Text(string='Header Memo')
    footerMemo = fields.Text(string='Footer Memo')
    checksum = fields.Text(string='Checksum')
    remark = fields.Text(string='Remark')
    approvedBy = fields.Char(string='Approved By')

    totalWithoutTax = fields.Float(string='Total Without Tax')
    totalTax = fields.Float(string='Total Tax')
    totalTaxabl1 = fields.Float(string='Taxable Amount 1')
    totalTax1 = fields.Float(string='Tax Amount 1')
    totalTaxabl2 = fields.Float(string='Taxable Amount 2')
    totalTax2 = fields.Float(string='Tax Amount 2')
    totalTaxabl3 = fields.Float(string='Taxable Amount 3')
    totalTax3 = fields.Float(string='Tax Amount 3')
    totalNonTax = fields.Float(string='Non-Taxable Total')
    totalWithTax = fields.Float(string='Total with Tax')
    totalPaid = fields.Float(string='Total Paid')
    totalDiscount = fields.Float(string='Total Discount')
    totalServiceCharge = fields.Float(string='Total Service Charge')
    total = fields.Float(string='Grand Total')
    change = fields.Float(string='Change')

    zReportSent = fields.Boolean(string='Z-Report Sent')
    printed = fields.Boolean(string='Printed')
    date = fields.Date(string='Date')
    time = fields.Char(string='Time')
    qrCodeData = fields.Text(string='QR Code Data')
    itemCount = fields.Integer(string='Item Count')
    zNo = fields.Integer(string='Z Number')  # Missing in original model

    globalDiscountType = fields.Char(string='Global Discount Type')
    globalDiscountAmount = fields.Float(string='Global Discount Amount')
    globalServiceChargeType = fields.Char(string='Global Service Charge Type')
    globalServiceChargeAmount = fields.Float(string='Global Service Charge Amount')

    printCopy = fields.Integer(string='Print Copies')
    ejPath = fields.Char(string='EJ Path')

    device_id = fields.Many2one('pos.device', string='Device')
    line_ids = fields.One2many('pos.invoice.line', 'invoice_id', string='Invoice Lines')
    
    # Reconciliation fields
    reconciliation_job_uuid = fields.Char('Reconciliation Job UUID', copy=False)
    reconciliation_status = fields.Selection([
        ('pending', 'Pending'),
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed')
    ], default='pending', string='Reconciliation Status')
    
    _sql_constraints = [
        ('fsNumber_device_id_unique', 'UNIQUE(fsNumber, device_id)', 'FS Number must be unique per device.')
    ]
    
    @api.model_create_multi
    def create(self, vals_list):
        invoices = super().create(vals_list)
        _logger.info(f"Created {len(invoices)} POS Invoices with FS Numbers: {[inv.fsNumber for inv in invoices]}")
        # Queue reconciliation for each created invoice
        # for invoice in invoices:
        #     # invoice._queue_reconciliation()
        # _logger.info("Queued reconciliation for newly created invoices.")
        return invoices
    
    def _queue_reconciliation(self):
        """Queue a reconciliation job with 10 second delay"""
        _logger.info("Queueing reconciliation for POS Invoices...")
        for invoice in self:
            if invoice.device_id and invoice.fsNumber:
                # Check if queue_job module is installed
                if 'queue.job' in self.env:
                    try:
                        # Use queue job for delayed execution
                        delayed_job = invoice.with_delay(
                            priority=10,
                            eta=fields.Datetime.now() + timedelta(seconds=10),
                            description=f'Reconcile Invoice FS#{invoice.fsNumber}'
                        ).process_invoice_reconciliation()
                        
                        # Store job UUID for tracking
                        invoice.write({
                            'reconciliation_job_uuid': delayed_job.uuid,
                            'reconciliation_status': 'queued'
                        })
                        
                        _logger.info(f"Queued reconciliation for Invoice FS#{invoice.fsNumber}, Job: {delayed_job.uuid}")
                    except Exception as e:
                        _logger.warning(f"Queue job not available, scheduling cron job instead: {e}")
                        self._schedule_reconciliation_cron()
                else:
                    # Fallback to cron job if queue_job not installed
                    self._schedule_reconciliation_cron()
    
    def _schedule_reconciliation_cron(self):
        """Fallback method using cron job if queue_job is not available"""
        for invoice in self:
            if invoice.device_id and invoice.fsNumber:
                run_date = fields.Datetime.now() + timedelta(seconds=10)
                cron_vals = {
                    'name': f'Reconcile Invoice FS#{invoice.fsNumber}',
                    'model_id': self.env['ir.model'].search([('model', '=', 'pos.invoice')], limit=1).id,
                    'state': 'code',
                    'code': f'env["pos.invoice"].browse({invoice.id}).process_invoice_reconciliation()',
                    'nextcall': run_date,
                    'numbercall': 1,
                    'interval_type': 'minutes',
                    'interval_number': 1,
                    'active': True,
                }
                self.env['ir.cron'].sudo().create(cron_vals)
                invoice.reconciliation_status = 'queued'
                _logger.info(f"Scheduled reconciliation for Invoice FS#{invoice.fsNumber} at {run_date}")
    
    def process_invoice_reconciliation(self):
        """Process reconciliation using existing run_reconciliation_check"""
        self.ensure_one()
        
        try:
            self.reconciliation_status = 'processing'
            
            # Get the MRC from device
            target_mrc = self.device_id.mrc
            invoice_date = self.date
            
            # Check if there's already an ongoing reconciliation for this MRC/date
            if self._is_reconciliation_running(target_mrc, invoice_date):
                _logger.info(f"Reconciliation already running for MRC {target_mrc} on {invoice_date}")
                self.reconciliation_status = 'pending'
                # Re-queue for later
                if 'queue.job' in self.env:
                    self.with_delay(
                        priority=15,
                        eta=fields.Datetime.now() + timedelta(seconds=30)
                    ).process_invoice_reconciliation()
                return
            
            # Use the existing run_reconciliation_check method with auto-invoice context
            result = self.env['pos.order'].with_context(
                auto_invoice_created=True  # Enable auto-invoicing for created orders
            ).run_reconciliation_check(
                target_mrc=target_mrc,
                start_date=invoice_date,
                end_date=invoice_date
            )
            
            if result.get('status') == 'success':
                self.reconciliation_status = 'done'
                _logger.info(f"✅ Reconciliation completed for Invoice FS#{self.fsNumber}")
            else:
                self.reconciliation_status = 'failed'
                _logger.warning(f"⚠️ Reconciliation failed for Invoice FS#{self.fsNumber}")
                
        except Exception as e:
            _logger.error(f"❌ Failed to reconcile invoice {self.id}: {str(e)}")
            self.reconciliation_status = 'failed'
            if 'queue.job' in self.env:
                raise  # Re-raise for queue job retry mechanism
    
    def _is_reconciliation_running(self, mrc, date):
        """Check if reconciliation is already running for this MRC and date"""
        running_jobs = self.search([
            ('device_id.mrc', '=', mrc),
            ('date', '=', date),
            ('reconciliation_status', '=', 'processing'),
            ('id', '!=', self.id)
        ])
        return bool(running_jobs)

class PosInvoiceLine(models.Model):
    _name = 'pos.invoice.line'
    _description = 'POS Invoice Line'

    invoice_id = fields.Many2one('pos.invoice', string='Invoice', ondelete='cascade')  # Maps to invoice_id_fk
    lineIndex = fields.Char(string='Line Index')
    pluCode = fields.Char(string='PLU Code')
    itemName = fields.Char(string='Item Name')
    itemShortName = fields.Char(string='Item Short Name')
    itemDescription = fields.Text(string='Item Description')

    quantity = fields.Float(string='Quantity')
    unit_name = fields.Char(string='Unit Name')
    price = fields.Float(string='Unit Price')

    lineDiscount = fields.Float(string='Line Discount')
    lineDiscountAmount = fields.Float(string='Line Discount Amount')
    lineDiscountType = fields.Char(string='Line Discount Type')

    lineServiceCharge = fields.Float(string='Line Service Charge')
    lineServiceChargeAmount = fields.Float(string='Line Service Charge Amount')
    lineServiceChargeType = fields.Char(string='Line Service Charge Type')

    date = fields.Date(string='Date')
    time = fields.Char(string='Time')

    lineTotal = fields.Float(string='Line Total')
    lineTotalTax = fields.Float(string='Line Total Tax')
    lineTotalWithTax = fields.Float(string='Line Total with Tax')

    taxAmount = fields.Float(string='Tax Amount')
    taxRate = fields.Float(string='Tax Rate')

    isVoided = fields.Boolean(string='Voided')