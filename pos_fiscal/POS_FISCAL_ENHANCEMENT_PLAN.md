# POS Fiscal Module Enhancement Plan

## Overview
The pos_fiscal module currently handles reconciliation correctly through `pos_order_reconcile_new.py`. This enhancement plan will improve the user experience and add automated reconciliation features using the existing reconciliation logic with queue jobs for better performance.

## Enhancement Components

### 1. Enhanced Wizard UI for FS Check
**Goal:** Create a more detailed and visually appealing reconciliation wizard

#### Features to Add:
- **Real-time Preview Panel**
  - Display current statistics before running reconciliation
  - Show invoice count, order count, and potential issues
  - Preview duplicate FS numbers
  - Show missing orders that will be created

- **Progress Tracking**
  - Step-by-step progress indicator
  - Real-time logs display
  - Success/error counters
  - Estimated time remaining

- **Enhanced Results Display**
  - Summary cards with icons
  - Color-coded status indicators
  - Detailed reconciliation report
  - Export results to PDF/Excel

#### Enhanced Wizard Implementation:
```python
# wizard/pos_fs_check_wizard.py
from odoo import models, fields, api
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class PosFsCheckWizard(models.TransientModel):
    _inherit = 'pos.fs.check.wizard'
    
    # Enhanced fields for better UI
    show_preview = fields.Boolean(string='Show Preview', default=True)
    auto_fix_duplicates = fields.Boolean(string='Auto Fix Duplicates', default=True)
    auto_create_missing = fields.Boolean(string='Auto Create Missing Orders', default=True)
    auto_invoice_created = fields.Boolean(string='Auto Invoice New Orders', default=True)
    use_queue_jobs = fields.Boolean(string='Use Queue Jobs', default=True)
    send_email_report = fields.Boolean(string='Send Email Report', default=False)
    email_recipients = fields.Char(string='Email Recipients')
    
    # Preview fields
    preview_data = fields.Html(string='Preview Data', compute='_compute_preview')
    estimated_time = fields.Char(string='Estimated Time', compute='_compute_estimated_time')
    last_run_summary = fields.Html(string='Last Run Summary', compute='_compute_last_run')
    pending_jobs_count = fields.Integer(string='Pending Jobs', compute='_compute_pending_jobs')
    
    # Progress tracking
    progress_percentage = fields.Integer(string='Progress', default=0)
    current_step = fields.Char(string='Current Step')
    log_messages = fields.Text(string='Log Messages')
    result_summary = fields.Html(string='Result Summary')
    
    @api.depends('company_id', 'target_mrc_id', 'start_date', 'end_date')
    def _compute_preview(self):
        for wizard in self:
            if not wizard.target_mrc_id or not wizard.start_date:
                wizard.preview_data = '<p>Select MRC and dates to preview</p>'
                continue
                
            # Get preview statistics
            mrc = wizard.target_mrc_id.mrc
            
            # Count invoices
            invoice_count = self.env['pos.invoice'].search_count([
                ('device_id', '=', wizard.target_mrc_id.id),
                ('date', '>=', wizard.start_date),
                ('date', '<=', wizard.end_date)
            ])
            
            # Count orders
            order_count = self.env['pos.order'].search_count([
                ('fiscal_mrc', '=', mrc),
                ('date_order', '>=', wizard.start_date),
                ('date_order', '<=', wizard.end_date),
                ('state', '!=', 'cancel')
            ])
            
            # Find duplicates
            duplicates = self.env['pos.order'].check_duplicate_fs(mrc, wizard.start_date)
            
            preview_html = f"""
            <div class="row">
                <div class="col-md-4">
                    <div class="card bg-info">
                        <div class="card-body text-center">
                            <h3>{invoice_count}</h3>
                            <p>Invoices</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-success">
                        <div class="card-body text-center">
                            <h3>{order_count}</h3>
                            <p>Orders</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-warning">
                        <div class="card-body text-center">
                            <h3>{len(duplicates)}</h3>
                            <p>Duplicates</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="mt-3">
                <h5>Issues to be fixed:</h5>
                <ul>
                    <li>Missing Orders: {invoice_count - order_count}</li>
                    <li>Duplicate FS Numbers: {len(duplicates)}</li>
                </ul>
            </div>
            """
            wizard.preview_data = preview_html
    
    def action_run_fs_check_enhanced(self):
        """Enhanced FS check with auto-invoicing"""
        self.ensure_one()
        
        try:
            target_mrc_value = self.target_mrc_id.mrc if self.target_mrc_id else None
            
            # Add context for auto-invoicing
            context = dict(self.env.context)
            context['auto_invoice_created'] = self.auto_invoice_created
            
            if self.use_queue_jobs:
                # Queue the reconciliation job
                job = self.env['pos.order'].with_context(context).with_delay(
                    priority=10,
                    description=f'Reconciliation for MRC {target_mrc_value}'
                ).run_reconciliation_check(
                    target_mrc=target_mrc_value,
                    start_date=self.start_date,
                    end_date=self.end_date,
                )
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Reconciliation Queued',
                        'message': f'Job {job.uuid} queued for MRC {target_mrc_value}',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                # Run immediately
                result = self.env['pos.order'].with_context(context).run_reconciliation_check(
                    target_mrc=target_mrc_value,
                    start_date=self.start_date,
                    end_date=self.end_date,
                )
                
                # Generate result summary
                self._generate_result_summary(result)
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Reconciliation Complete',
                        'message': f"Processed {result.get('order_count', 0)} orders",
                        'type': 'success',
                        'sticky': False,
                    }
                }
                
        except Exception as e:
            _logger.exception("Error running enhanced FS check: %s", e)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Reconciliation Error',
                    'message': str(e),
                    'type': 'danger',
                    'sticky': False,
                }
            }
```

### 2. Auto-Reconciliation with Queue Jobs (10 Second Delay)
**Goal:** Automatically reconcile when a new pos.invoice is created using the existing `run_reconciliation_check` method

#### Implementation using existing reconciliation logic:
```python
# models/pos_invoice.py
from odoo import models, fields, api
from odoo.addons.queue_job.job import job
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)

class PosInvoice(models.Model):
    _inherit = 'pos.invoice'
    
    reconciliation_job_uuid = fields.Char('Reconciliation Job UUID', copy=False)
    reconciliation_status = fields.Selection([
        ('pending', 'Pending'),
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed')
    ], default='pending', string='Reconciliation Status')
    
    @api.model
    def create(self, vals):
        invoice = super().create(vals)
        # Queue reconciliation job with 10 second delay
        invoice._queue_reconciliation()
        return invoice
    
    def _queue_reconciliation(self):
        """Queue a reconciliation job with 10 second delay"""
        for invoice in self:
            if invoice.device_id and invoice.fsNumber:
                # Create a delayed job using existing reconciliation
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
    
    @job
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
                _logger.info(f"Reconciliation completed for Invoice FS#{self.fsNumber}")
            else:
                self.reconciliation_status = 'failed'
                _logger.warning(f"Reconciliation failed for Invoice FS#{self.fsNumber}")
                
        except Exception as e:
            _logger.error(f"Failed to reconcile invoice {self.id}: {str(e)}")
            self.reconciliation_status = 'failed'
            raise
    
    def _is_reconciliation_running(self, mrc, date):
        """Check if reconciliation is already running for this MRC and date"""
        running_jobs = self.search([
            ('device_id.mrc', '=', mrc),
            ('date', '=', date),
            ('reconciliation_status', '=', 'processing'),
            ('id', '!=', self.id)
        ])
        return bool(running_jobs)
```

### 3. Update Existing pos_order_reconcile_new.py for Auto-Invoicing
**Goal:** Add auto-invoicing capability to the existing `_create_order_from_invoice` method

#### Enhanced Implementation in pos_order_reconcile_new.py:
```python
# models/pos_order_reconcile_new.py
# Update the existing _create_order_from_invoice method (around line 666)

def _create_order_from_invoice(self, invoice_data, target_mrc, daily_report):
    """Create new order from invoice data with auto-invoicing support"""
    try:
        # Get invoice record
        invoice_rec = self.env['pos.invoice'].browse(invoice_data['id'])
        
        # Find appropriate session
        invoice_date = fields.Datetime.from_string(invoice_data['date']).date()
        session = self._find_or_create_session(target_mrc, invoice_date)
        
        if not session:
            _logger.warning("⚠️ Cannot find/create session for invoice FS %s", invoice_data['fsNumber'])
            return False
        
        # Prepare order values
        order_vals = self._prepare_pos_order_vals(invoice_rec, target_mrc, session.id)
        
        if not order_vals:
            _logger.warning("⚠️ Cannot prepare order values for invoice FS %s", invoice_data['fsNumber'])
            return False
        
        # Create order
        new_order = self.create(order_vals)
        new_order.write({'state': 'done'})
        
        # Log creation
        self.env['pos.change.log'].log_change(
            pos_order_id=new_order.id,
            fs_no=str(invoice_data['fsNumber']).zfill(8),
            fiscal_mrc=target_mrc,
            change_type='recreated',
            old_value='none',
            new_value='created from invoice',
            daily_report_id=daily_report.id
        )
        
        _logger.info("✅ Created order %s from invoice FS %s", new_order.id, invoice_data['fsNumber'])
        
        # AUTO-INVOICE THE CREATED ORDER (NEW PART)
        if new_order and self.env.context.get('auto_invoice_created', False):
            _logger.info("🔄 Auto-invoicing order FS No: %s (ID: %s)", invoice_data['fsNumber'], new_order.id)
            try:
                # Ensure order is in correct state for invoicing
                if new_order.state not in ['paid', 'done', 'invoiced']:
                    new_order.write({'state': 'paid'})
                
                # Create invoice using Odoo's standard method
                invoice = new_order.action_pos_order_invoice()
                
                _logger.info("✅ POS Order invoiced successfully for FS No: %s", invoice_data['fsNumber'])
                
                # Log auto-invoicing
                self.env['pos.change.log'].log_change(
                    pos_order_id=new_order.id,
                    fs_no=str(invoice_data['fsNumber']).zfill(8),
                    fiscal_mrc=target_mrc,
                    change_type='auto_invoiced',
                    old_value='no_invoice',
                    new_value='invoiced',
                    daily_report_id=daily_report.id
                )
                
            except Exception as e:
                _logger.warning("⚠️ Failed to invoice order FS No: %s due to: %s", invoice_data['fsNumber'], str(e))
                _logger.info("ℹ️ Order FS No: %s created but not invoiced", invoice_data['fsNumber'])
        
        return True
        
    except Exception as e:
        _logger.error("❌ Failed to create order from invoice FS %s: %s", 
                     invoice_data['fsNumber'], str(e))
        return False

# Also update the _validate_orders_against_invoices method to pass context
def _validate_orders_against_invoices(self, invoice_map, order_map, target_mrc, start_date, end_date, daily_report):
    """
    Validate all orders against invoices with auto-invoicing support
    """
    stats = {'created': 0, 'updated': 0, 'unmatched': 0}
    processed_fs = set()
    
    # Get auto-invoice setting from context
    auto_invoice = self.env.context.get('auto_invoice_created', False)
    
    for fs_key, invoice_data in invoice_map.items():
        if fs_key in processed_fs:
            continue
        
        existing_order = order_map.get(fs_key)
        
        if not existing_order:
            # Check for order with various FS formats
            fs_variations = [
                str(fs_key),
                str(fs_key).zfill(8),
                str(fs_key).lstrip('0'),
            ]
            
            existing_order_rec = None
            for fs_var in fs_variations:
                existing_order_rec = self.search([
                    ('fs_no', '=', fs_var),
                    ('fiscal_mrc', '=', target_mrc),
                    ('state', '!=', 'cancel')
                ], limit=1)
                if existing_order_rec:
                    break
            
            if existing_order_rec:
                # Update existing order
                self._sync_order_with_invoice(existing_order_rec, invoice_data, daily_report)
                stats['updated'] += 1
            else:
                # Create new order from invoice with auto-invoicing
                if self.with_context(auto_invoice_created=auto_invoice)._create_order_from_invoice(
                    invoice_data, target_mrc, daily_report
                ):
                    stats['created'] += 1
                else:
                    stats['unmatched'] += 1
        else:
            # Check if update needed
            order_rec = self.browse(existing_order['id'])
            if self._needs_update(order_rec, invoice_data):
                self._sync_order_with_invoice(order_rec, invoice_data, daily_report)
                stats['updated'] += 1
        
        processed_fs.add(fs_key)
    
    return stats

# Update PosChangeLog to include auto_invoiced type
class PosChangeLog(models.Model):
    _inherit = 'pos.change.log'
    
    change_type = fields.Selection([
        ('recreated', 'Order Recreated'),
        ('amount_updated', 'Amount Updated'),
        ('cancelled', 'Order Cancelled'),
        ('linked', 'Order Linked'),
        ('updated_from_invoice', 'Updated from Invoice'),
        ('complete_update', 'Complete Update'),
        ('auto_invoiced', 'Auto Invoiced'),  # Add this new type
    ], string='Change Type', required=True)
```

### 4. Daily Cron Job for Multi-Company Reconciliation
**Goal:** Automatically reconcile all companies and machines at day end using existing reconciliation

#### Cron Configuration:
```xml
<!-- data/cron_data.xml -->
<odoo>
    <record id="ir_cron_daily_reconciliation" model="ir.cron">
        <field name="name">Daily POS Reconciliation</field>
        <field name="model_id" ref="model_pos_order"/>
        <field name="state">code</field>
        <field name="code">model._queue_daily_reconciliation_all_companies()</field>
        <field name="interval_number">1</field>
        <field name="interval_type">days</field>
        <field name="numbercall">-1</field>
        <field name="doall" eval="False"/>
        <field name="nextcall">2025-01-21 23:30:00</field>
        <field name="active" eval="True"/>
    </record>
</odoo>
```

#### Implementation using existing reconciliation:
```python
# models/pos_order_reconcile_new.py
# Add these methods to PosOrder class

@api.model
def _queue_daily_reconciliation_all_companies(self):
    """Queue reconciliation jobs for all companies using existing logic"""
    companies = self.env['res.company'].search([])
    job_uuids = []
    
    for company in companies:
        devices = self.env['pos.device'].search([
            ('company_id', '=', company.id),
            ('active', '=', True)
        ])
        
        for device in devices:
            # Queue a job for each device with staggered execution
            delay_minutes = len(job_uuids) * 2  # 2 minutes between each job
            
            # Use existing run_reconciliation_check with auto-invoice context
            job = self.with_company(company).with_context(
                auto_invoice_created=True
            ).with_delay(
                priority=20,
                eta=fields.Datetime.now() + timedelta(minutes=delay_minutes),
                description=f'Daily Reconciliation: {company.name} - {device.name}'
            ).run_reconciliation_check(
                target_mrc=device.mrc,
                start_date=fields.Date.today(),
                end_date=fields.Date.today()
            )
            
            job_uuids.append(job.uuid)
            _logger.info(f"Queued reconciliation for {company.name} - {device.name}: Job {job.uuid}")
    
    # Queue a summary job to run after all reconciliations
    summary_delay = len(job_uuids) * 2 + 10  # After all jobs + 10 minutes
    self.with_delay(
        priority=25,
        eta=fields.Datetime.now() + timedelta(minutes=summary_delay),
        description='Daily Reconciliation Summary'
    )._send_daily_reconciliation_summary(fields.Date.today())
    
    return job_uuids

@job
def _send_daily_reconciliation_summary(self, target_date):
    """Send summary email after all reconciliations complete"""
    # Fetch all daily reports for today
    daily_reports = self.env['pos.daily.report'].search([
        ('date', '=', target_date)
    ])
    
    if not daily_reports:
        _logger.warning("No daily reports found for %s", target_date)
        return
    
    # Prepare summary data
    summary_html = f"""
    <h3>Daily Reconciliation Summary - {target_date}</h3>
    <table border="1" style="border-collapse: collapse; width: 100%;">
        <thead>
            <tr>
                <th>Company</th>
                <th>MRC</th>
                <th>Orders</th>
                <th>Invoices</th>
                <th>Order Total</th>
                <th>Invoice Total</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for report in daily_reports:
        status_color = 'green' if report.reconciliation_status == 'completed' else 'red'
        summary_html += f"""
            <tr>
                <td>{report.company_id.name}</td>
                <td>{report.fiscal_mrc}</td>
                <td>{report.pos_order_count}</td>
                <td>{report.invoice_count}</td>
                <td>{report.net_order_total:.2f}</td>
                <td>{report.net_invoice_total:.2f}</td>
                <td style="color: {status_color};">{report.reconciliation_status}</td>
            </tr>
        """
    
    summary_html += """
        </tbody>
    </table>
    """
    
    # Send email to administrators
    self._send_reconciliation_email(summary_html)
    
    return True

def _send_reconciliation_email(self, content):
    """Send reconciliation summary email"""
    try:
        mail_template = self.env.ref('pos_fiscal.daily_reconciliation_email_template', raise_if_not_found=False)
        if mail_template:
            mail_template.send_mail(self.id, force_send=True)
        else:
            # Create simple email
            mail_values = {
                'subject': f'Daily POS Reconciliation Report - {fields.Date.today()}',
                'body_html': content,
                'email_to': 'admin@company.com',  # Configure this
                'email_from': 'noreply@company.com',
            }
            self.env['mail.mail'].create(mail_values).send()
    except Exception as e:
        _logger.error("Failed to send reconciliation email: %s", str(e))
```

## Enhanced Wizard View

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_pos_fs_check_wizard_form_enhanced" model="ir.ui.view">
        <field name="name">pos.fs.check.wizard.form.enhanced</field>
        <field name="model">pos.fs.check.wizard</field>
        <field name="priority">20</field>
        <field name="arch" type="xml">
            <form string="POS Reconciliation Center">
                <sheet>
                    <div class="oe_title">
                        <h1>
                            <i class="fa fa-sync-alt text-primary"/> POS Fiscal Reconciliation
                        </h1>
                    </div>
                    
                    <!-- Queue Jobs Status -->
                    <div class="alert alert-info" attrs="{'invisible': [('pending_jobs_count', '=', 0)]}">
                        <i class="fa fa-clock"/> <field name="pending_jobs_count"/> reconciliation jobs in queue
                    </div>
                    
                    <notebook>
                        <!-- Configuration Tab -->
                        <page string="Configuration" name="config">
                            <group>
                                <group string="Target Selection">
                                    <field name="company_id" options="{'no_create': True}"/>
                                    <field name="allowed_device_ids" invisible="1"/>
                                    <field name="target_mrc_id" 
                                           domain="[('id', 'in', allowed_device_ids)]"
                                           options="{'no_create': True}"/>
                                </group>
                                <group string="Date Range">
                                    <field name="start_date"/>
                                    <field name="end_date"/>
                                </group>
                            </group>
                            
                            <separator string="Reconciliation Options"/>
                            <group col="4">
                                <field name="auto_fix_duplicates" widget="boolean_toggle"/>
                                <field name="auto_create_missing" widget="boolean_toggle"/>
                                <field name="auto_invoice_created" widget="boolean_toggle"/>
                                <field name="show_preview" widget="boolean_toggle"/>
                                <field name="use_queue_jobs" widget="boolean_toggle"/>
                                <field name="send_email_report" widget="boolean_toggle"/>
                            </group>
                        </page>
                        
                        <!-- Preview Tab -->
                        <page string="Preview" name="preview" attrs="{'invisible': [('show_preview', '=', False)]}">
                            <field name="preview_data" widget="html" readonly="1" nolabel="1"/>
                        </page>
                        
                        <!-- Results Tab -->
                        <page string="Results" name="results" attrs="{'invisible': [('result_summary', '=', False)]}">
                            <field name="result_summary" widget="html" readonly="1" nolabel="1"/>
                        </page>
                    </notebook>
                </sheet>
                
                <footer>
                    <button name="action_run_fs_check_enhanced" 
                            string="Run Reconciliation" 
                            type="object" 
                            class="btn-primary"/>
                    <button name="action_schedule_daily" 
                            string="Schedule Daily" 
                            type="object" 
                            class="btn-warning"/>
                    <button string="Cancel" class="btn-default" special="cancel"/>
                </footer>
            </form>
        </field>
    </record>
</odoo>
```

## Key Implementation Points

1. **Uses Existing Reconciliation Logic**
   - All reconciliation continues to use `run_reconciliation_check` from `pos_order_reconcile_new.py`
   - No changes to the core reconciliation algorithm
   - Only adds auto-invoicing capability

2. **Auto-Invoicing Integration**
   - Added to `_create_order_from_invoice` method
   - Controlled by context variable `auto_invoice_created`
   - Uses standard Odoo `action_pos_order_invoice` method

3. **Queue Job Benefits**
   - Non-blocking processing
   - Better performance for real-time reconciliation
   - Prevents timeout issues
   - Automatic retry on failure

4. **Minimal Code Changes**
   - Only modifies the order creation method to add invoicing
   - Preserves all existing reconciliation logic
   - Backward compatible

## Installation Requirements

```python
# __manifest__.py update
{
    'name': 'POS Fiscal',
    'depends': [
        'base',
        'point_of_sale',
        'queue_job',  # Add this dependency
    ],
    'data': [
        'data/cron_data.xml',
        'views/pos_fs_check_wizard.xml',
        # ... other data files
    ],
}
```

## Testing Checklist

- [ ] Test manual reconciliation without auto-invoicing
- [ ] Test manual reconciliation with auto-invoicing enabled
- [ ] Test automatic reconciliation on invoice creation
- [ ] Test daily cron job for multiple companies
- [ ] Verify invoice creation for missing orders
- [ ] Check change logs for auto-invoiced orders
- [ ] Verify email reports are sent correctly

## Success Metrics

- Reconciliation uses existing proven logic
- Auto-invoicing success rate: > 95%
- Queue processing time: < 30 seconds per invoice
- System maintains backward compatibility
- Minimal code changes to existing system