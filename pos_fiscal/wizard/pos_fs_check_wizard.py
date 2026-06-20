from odoo import models, fields, api
import logging
from datetime import datetime, timedelta
from markupsafe import Markup

_logger = logging.getLogger(__name__)

class PosFsCheckWizard(models.TransientModel):
    _name = 'pos.fs.check.wizard'
    _description = 'POS FS Check Wizard'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    target_mrc_id = fields.Many2one(
        'pos.device',
        string='Target MRC',
        help='Select the fiscal device (MRC) for this company.'
    )

    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.today)
    end_date = fields.Date(string='End Date', required=True, default=fields.Date.today)
    allowed_device_ids = fields.Many2many(
            'pos.device', compute='_compute_allowed_devices', store=False
        )
    
    # Enhanced fields for better UI
    show_preview = fields.Boolean(string='Show Preview', default=True)
    auto_fix_duplicates = fields.Boolean(string='Auto Fix Duplicates', default=True)
    auto_create_missing = fields.Boolean(string='Auto Create Missing Orders', default=True)
    auto_invoice_created = fields.Boolean(string='Auto Invoice New Orders', default=True)
    create_inventory_picking = fields.Boolean(string='Create Inventory Pickings', default=True,
        help='Create stock pickings for reconciled orders to update inventory')
    update_inventory_on_sync = fields.Boolean(string='Update Inventory on Sync', default=True,
        help='Create inventory pickings when syncing existing orders with changed amounts')
    update_accounting_on_sync = fields.Boolean(string='Update Accounting on Sync', default=False,
        help='Flag orders with posted invoices that need accounting review (safer than auto-update)')
    use_queue_jobs = fields.Boolean(string='Use Queue Jobs', default=False)
    send_email_report = fields.Boolean(string='Send Email Report', default=False)
    email_recipients = fields.Char(string='Email Recipients')
    
    # Configuration display
    config_summary = fields.Html(string='Current Configuration', compute='_compute_config_summary', sanitize=False)

    # Preview fields
    preview_data = fields.Html(string='Preview Data', compute='_compute_preview', sanitize=False)
    estimated_time = fields.Char(string='Estimated Time', compute='_compute_estimated_time')
    last_run_summary = fields.Html(string='Last Run Summary', compute='_compute_last_run', sanitize=False)
    pending_jobs_count = fields.Integer(string='Pending Jobs', compute='_compute_pending_jobs')
    
    # Progress tracking
    progress_percentage = fields.Integer(string='Progress', default=0)
    current_step = fields.Char(string='Current Step')
    log_messages = fields.Text(string='Log Messages')
    result_summary = fields.Html(string='Result Summary', sanitize=False)
    has_errors = fields.Boolean(string='Has Errors', default=False)
    @api.depends('company_id')
    def _compute_allowed_devices(self):
        for rec in self:
            if rec.company_id:
                rec.allowed_device_ids = self.env['pos.device'].search([('company_id', '=', rec.company_id.id)])
            else:
                rec.allowed_device_ids = self.env['pos.device'].browse()
    @api.onchange('company_id')
    def _onchange_company_id(self):
        _logger.info("Onchange company_id called: %s", self.company_id.name if self.company_id else 'No company')
        self.target_mrc_id = False
        if not self.company_id:
            return {'domain': {'target_mrc_id': []}}

        devices = self.env['pos.device'].search([('company_id', '=', self.company_id.id)])
        _logger.info("✅ Found devices for %s: %s", self.company_id.name, devices.mapped('name'))

        return {
            'domain': {'target_mrc_id': [('id', 'in', devices.ids)]}
        }

    def _get_mrc_selection_for_company(self, company_id):
        _logger.info("📡 Fetching distinct fiscal_mrc for company ID=%s", company_id)

        self.env.cr.execute("""
            SELECT DISTINCT fiscal_mrc
            FROM pos_order
            WHERE company_id = %s
              AND fiscal_mrc IS NOT NULL
              AND fiscal_mrc != ''
            ORDER BY fiscal_mrc
        """, (company_id,))
        rows = self.env.cr.fetchall()

        if not rows:
            _logger.warning("⚠ No fiscal_mrc found for company ID=%s", company_id)

        selection_list = [(r[0], r[0]) for r in rows]
        _logger.info("📋 MRC selection list built: %s", selection_list)
        return selection_list

    @api.depends('company_id', 'target_mrc_id')
    def _compute_config_summary(self):
        """Display effective configuration for selected device/company"""
        for wizard in self:
            if wizard.target_mrc_id:
                # Get device-specific config
                config = wizard.target_mrc_id.get_reconciliation_config()
                config_source = "Device-Specific" if wizard.target_mrc_id.use_custom_config else "Global"
            elif wizard.company_id:
                # Get global config from system parameters
                ICP = self.env['ir.config_parameter'].sudo()
                enable_inventory = ICP.get_param('pos_fiscal.enable_inventory_integration', default='True') == 'True'
                enable_accounting = ICP.get_param('pos_fiscal.enable_accounting_integration', default='True') == 'True'

                config = {
                    'auto_invoice_created': enable_accounting and ICP.get_param('pos_fiscal.auto_invoice_created_orders', default='True') == 'True',
                    'create_inventory_picking': enable_inventory and ICP.get_param('pos_fiscal.create_picking_on_create', default='True') == 'True',
                    'update_inventory_on_sync': enable_inventory and ICP.get_param('pos_fiscal.create_picking_on_sync', default='True') == 'True',
                }
                config_source = "Global"
            else:
                wizard.config_summary = Markup('<p>Select company to see configuration</p>')
                continue

            inventory_icon = "✅" if config.get('create_inventory_picking') else "❌"
            accounting_icon = "✅" if config.get('auto_invoice_created') else "❌"

            summary_html = f"""
            <div class="alert alert-info">
                <h5><i class="fa fa-cog"/> {config_source} Configuration</h5>
                <table class="table table-sm table-borderless">
                    <tr>
                        <td><b>{inventory_icon} Inventory Integration:</b></td>
                        <td>{'Enabled' if config.get('create_inventory_picking') else 'Disabled'}</td>
                    </tr>
                    <tr>
                        <td><b>{accounting_icon} Accounting Integration:</b></td>
                        <td>{'Enabled' if config.get('auto_invoice_created') else 'Disabled'}</td>
                    </tr>
                    <tr>
                        <td><b>Auto-Invoice Orders:</b></td>
                        <td>{'Yes' if config.get('auto_invoice_created') else 'No'}</td>
                    </tr>
                    <tr>
                        <td><b>Create Stock Pickings:</b></td>
                        <td>{'Yes' if config.get('create_inventory_picking') else 'No'}</td>
                    </tr>
                    <tr>
                        <td><b>Update on Sync:</b></td>
                        <td>{'Yes' if config.get('update_inventory_on_sync') else 'No'}</td>
                    </tr>
                </table>
                <p class="mb-0">
                    <a href="#" class="oe_link">
                        <i class="fa fa-external-link-alt"/>
                        Go to Settings → Companies → POS Fiscal to change configuration
                    </a>
                </p>
            </div>
            """
            wizard.config_summary = Markup(summary_html)

    @api.depends('company_id', 'target_mrc_id', 'start_date', 'end_date')
    def _compute_preview(self):
        for wizard in self:
            if not wizard.target_mrc_id or not wizard.start_date:
                wizard.preview_data = Markup('<p>Select MRC and dates to preview</p>')
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
                    <li>Missing Orders: {invoice_count - order_count if invoice_count > order_count else 0}</li>
                    <li>Duplicate FS Numbers: {len(duplicates)}</li>
                </ul>
            </div>
            """
            wizard.preview_data = Markup(preview_html)
    
    @api.depends('start_date', 'end_date')
    def _compute_estimated_time(self):
        for wizard in self:
            if wizard.start_date and wizard.end_date:
                days = (wizard.end_date - wizard.start_date).days + 1
                estimated_seconds = days * 30  # 30 seconds per day estimate
                wizard.estimated_time = f"{estimated_seconds} seconds"
            else:
                wizard.estimated_time = "Unknown"
    
    @api.depends('company_id', 'target_mrc_id')
    def _compute_last_run(self):
        for wizard in self:
            if not wizard.target_mrc_id:
                wizard.last_run_summary = Markup('<p>No previous runs</p>')
                continue
                
            # Get last daily report
            last_report = self.env['pos.daily.report'].search([
                ('fiscal_mrc', '=', wizard.target_mrc_id.mrc),
                ('company_id', '=', wizard.company_id.id)
            ], limit=1, order='date desc')
            
            if last_report:
                summary_html = f"""
                <div class="alert alert-info">
                    <strong>Last Run: {last_report.date}</strong><br/>
                    Orders: {last_report.pos_order_count} | 
                    Invoices: {last_report.invoice_count} | 
                    Created: {last_report.recreated_orders} | 
                    Updated: {last_report.updated_orders}
                </div>
                """
                wizard.last_run_summary = Markup(summary_html)
            else:
                wizard.last_run_summary = Markup('<p>No previous runs found</p>')
    
    def _compute_pending_jobs(self):
        for wizard in self:
            # Check for queue jobs if module is installed
            if 'queue.job' in self.env:
                wizard.pending_jobs_count = self.env['queue.job'].search_count([
                    ('state', 'in', ['pending', 'enqueued']),
                    ('model_name', 'in', ['pos.order', 'pos.invoice'])
                ])
            else:
                wizard.pending_jobs_count = 0

    def action_run_fs_check(self):
        """Enhanced FS check with auto-invoicing and inventory integration"""
        self.ensure_one()

        _logger.info(
            "🚀 Running Enhanced FS Check | Company=%s | MRC=%s | Start=%s | End=%s | Inventory=%s | Invoice=%s",
            self.company_id.name,
            self.target_mrc_id.name if self.target_mrc_id else 'None',
            self.start_date,
            self.end_date,
            self.create_inventory_picking,
            self.auto_invoice_created
        )

        try:
            target_mrc_value = self.target_mrc_id.mrc if self.target_mrc_id else None

            # Add context for auto-invoicing, inventory, and accounting
            context = dict(self.env.context)
            context['auto_invoice_created'] = self.auto_invoice_created
            context['create_inventory_picking'] = self.create_inventory_picking
            context['update_inventory_on_sync'] = self.update_inventory_on_sync
            context['update_accounting_on_sync'] = self.update_accounting_on_sync

            if self.use_queue_jobs and 'queue.job' in self.env:
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
                        'message': f'Job queued for MRC {target_mrc_value}',
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
            _logger.exception("❌ Error running enhanced FS check: %s", e)
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
    
    def _generate_result_summary(self, result):
        """Generate HTML summary of reconciliation results"""
        if not result:
            return
            
        summary_html = f"""
        <div class="row">
            <div class="col-12">
                <h4>Reconciliation Results</h4>
                <table class="table table-sm">
                    <tr><td>Status:</td><td><strong>{result.get('status', 'Unknown')}</strong></td></tr>
                    <tr><td>Orders Processed:</td><td>{result.get('order_count', 0)}</td></tr>
                    <tr><td>Invoices Processed:</td><td>{result.get('invoice_count', 0)}</td></tr>
                    <tr><td>Orders Created:</td><td>{result.get('metrics', {}).get('orders_created', 0)}</td></tr>
                    <tr><td>Orders Updated:</td><td>{result.get('metrics', {}).get('orders_updated', 0)}</td></tr>
                    <tr><td>Duplicates Fixed:</td><td>{result.get('metrics', {}).get('duplicates_resolved', 0)}</td></tr>
                    <tr><td>Processing Time:</td><td>{result.get('processing_time', 0):.2f} seconds</td></tr>
                </table>
            </div>
        </div>
        """
        self.result_summary = Markup(summary_html)
        self.has_errors = result.get('status') != 'success'
    
    def action_schedule_daily(self):
        """Schedule daily reconciliation cron job"""
        cron = self.env.ref('pos_fiscal.ir_cron_daily_reconciliation', raise_if_not_found=False)
        if cron:
            cron.active = True
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Daily Reconciliation Scheduled',
                    'message': 'Daily reconciliation will run at 23:30 every day',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'Could not find daily reconciliation cron job',
                    'type': 'danger',
                    'sticky': False,
                }
            }