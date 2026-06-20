from odoo import models, fields, api
import logging
from datetime import date, datetime, timedelta
from collections import defaultdict

_logger = logging.getLogger(__name__)

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def get_payment_method_id(self, payment_method, company_id, session_id):
        _logger.info("🚀 Entering get_payment_method_id with payment_method=%s, company_id=%s, session_id=%s", payment_method, company_id, session_id)
        try:
            normalized_payment = payment_method.strip().lower()
            session = self.env['pos.session'].browse(session_id) if session_id else None
            if not session:
                _logger.warning("⚠️ No session found for session_id: %s", session_id)
                session = self.env['pos.session'].search([('company_id', '=', company_id), ('state', '=', 'closed')], order='start_at desc', limit=1)
                if not session:
                    _logger.error("❌ No session found for company_id=%s", company_id)
                    return None, None, None
                session_id = session.id

            config = session.config_id
            payment = self.search([
                ('name', '=ilike', payment_method),
                ('company_id', '=', company_id),
            ], limit=1)
            if not payment:
                _logger.warning("⚠️ No payment method found for '%s' in company_id=%s", payment_method, company_id)
                payment = config.payment_method_ids.filtered(lambda pm: pm.company_id.id == company_id)[:1]
                if not payment:
                    payment = self.search([
                        ('name', '=ilike', 'Cash'),
                        ('company_id', '=', company_id),
                    ], limit=1)
                    if not payment:
                        _logger.error("❌ No default 'Cash' payment method found for company_id=%s", company_id)
                        return None, None, None

            if payment not in config.payment_method_ids:
                _logger.warning("⚠️ Payment method '%s' not in config ID=%s", payment.name, config.id)
                payment = config.payment_method_ids.filtered(lambda pm: pm.company_id.id == company_id)[:1] or self.search([
                    ('name', '=ilike', 'Cash'),
                    ('company_id', '=', company_id),
                ], limit=1)
                if not payment:
                    return None, None, None

            journal_name = payment.journal_id.name if payment.journal_id else None
            _logger.info("✅ Found payment method: %s (ID=%s), Journal: %s", payment.name, payment.id, journal_name)
            return payment.id, session_id, journal_name

        except Exception as e:
            _logger.exception("❌ Error in get_payment_method_id for '%s': %s", payment_method, str(e))
            return None, None, None

class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def run_reconciliation_check(self, target_mrc=None, start_date=None, end_date=None):
        """
        Enhanced reconciliation process with improved duplicate handling and invoice-based validation.
        
        This method ensures:
        1. Invoice (EJ) data is the source of truth
        2. FS numbers are unique per MRC
        3. Duplicates are resolved based on invoice matching
        4. Complete data synchronization from invoice to order
        """
        # Default values for testing
        if not target_mrc:
            target_mrc = "URB0000380"
        if not start_date:
            start_date = "2025-07-12"
        if not end_date:
            end_date = "2025-07-12"
        
        _logger.info("🚀 Starting enhanced reconciliation for MRC: %s from %s to %s", target_mrc, start_date, end_date)

        # Convert string dates to datetime.date if necessary
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Initialize performance metrics
        start_time = datetime.now()
        metrics = {
            'duplicates_found': 0,
            'duplicates_resolved': 0,
            'orders_created': 0,
            'orders_updated': 0,
            'orders_cancelled': 0,
            'orphans_linked': 0,
        }

        # Fetch device
        device = self.env['pos.device'].search([('mrc', '=', target_mrc)], limit=1)
        if not device:
            _logger.error("❌ No POS Device found with MRC: %s", target_mrc)
            return {'status': 'error', 'message': f"No POS Device found with MRC: {target_mrc}"}

        # Get configuration for this device/company
        config_context = device.get_reconciliation_config()

        # Merge with existing context (context params take precedence)
        effective_context = dict(config_context)
        for key in ['auto_invoice_created', 'create_inventory_picking', 'update_inventory_on_sync', 'update_accounting_on_sync']:
            if key in self.env.context:
                effective_context[key] = self.env.context[key]

        # Update context for this reconciliation run
        self = self.with_context(**effective_context)

        _logger.info("🔧 Reconciliation config: Inventory=%s, Accounting=%s",
                    effective_context.get('create_inventory_picking'),
                    effective_context.get('auto_invoice_created'))

        # Create daily report early for logging
        daily_report = self.env['pos.daily.report'].create({
            'date': start_date,
            'fiscal_mrc': target_mrc,
            'company_id': self.env.company.id,
        })

        # Fetch POS Orders
        pos_orders = self.search_read(
            [('fiscal_mrc', '=', target_mrc),
             ('date_order', '>=', start_date),
             ('date_order', '<=', end_date)],
            ['id', 'fiscal_mrc', 'fs_no', 'date_order', 'amount_total', 'state', 'pos_reference']
        )
        _logger.info("✅ %d POS Orders fetched", len(pos_orders))

        # Fetch POS Invoices (Source of Truth)
        invoice_model = self.env['pos.invoice']
        pos_invoices = invoice_model.search_read(
            [('device_id', '=', device.id),
             ('date', '>=', start_date),
             ('date', '<=', end_date)],
            ['id', 'fsNumber', 'totalWithTax', 'date', 'paymentType', 'cashierName', 
             'buyerName', 'referenceNumber', 'totalTax', 'totalPaid', 'change']
        )
        _logger.info("✅ %d POS Invoices fetched (Source of Truth)", len(pos_invoices))

        # Fetch POS Refunds
        refund_model = self.env['pos.refund']
        pos_refunds = refund_model.search_read(
            [('device_id', '=', device.id),
             ('date', '>=', start_date),
             ('date', '<=', end_date)],
            ['id', 'rfdNumber', 'totalWithTax', 'date', 'paymentType', 'cashierName', 'buyerName']
        )
        refund_total = sum(refund['totalWithTax'] for refund in pos_refunds)
        _logger.info("✅ %d POS Refunds fetched, Total: %.2f", len(pos_refunds), refund_total)

        # Fetch Z-Reports with exception handling
        zreport_model = self.env['pos.zreport']
        excluded_zreport_ids = self.env['pos.zreport.exception'].get_excluded_zreport_ids(target_mrc, start_date, end_date)
        
        all_zreports = zreport_model.search_read(
            [('device_id', '=', device.id),
             ('date', '>=', start_date),
             ('date', '<=', end_date)],
            ['id', 'salesTotal', 'rfdSalesTotal', 'date']
        )
        
        # Filter and deduplicate Z-reports
        zreports = self._process_zreports(all_zreports, excluded_zreport_ids)
        z_sales_total = sum(z['salesTotal'] for z in zreports)
        z_refund_total = sum(z['rfdSalesTotal'] for z in zreports)
        _logger.info("✅ %d Z-Reports processed, Sales: %.2f, Refunds: %.2f", 
                    len(zreports), z_sales_total, z_refund_total)

        # Build comprehensive invoice map (Source of Truth)
        invoice_map = self._build_invoice_map(pos_invoices)
        
        # Build order map for comparison
        order_map = self._build_order_map(pos_orders)

        # Phase 1: Enhanced Duplicate Resolution
        _logger.info("🔍 Phase 1: Enhanced Duplicate FS Resolution")
        duplicate_stats = self._resolve_duplicate_fs_numbers(
            target_mrc, start_date, end_date, invoice_map, daily_report
        )
        metrics.update(duplicate_stats)

        # Phase 2: Orphan Order Processing
        _logger.info("🔍 Phase 2: Processing Orphan Orders")
        orphan_stats = self._process_orphan_orders(
            target_mrc, start_date, end_date, invoice_map, daily_report
        )
        metrics['orphans_linked'] = orphan_stats['linked']
        metrics['orders_cancelled'] += orphan_stats['cancelled']

        # Phase 3: Invoice-Based Validation
        _logger.info("🔍 Phase 3: Invoice-Based Validation and Synchronization")
        validation_stats = self._validate_orders_against_invoices(
            invoice_map, order_map, target_mrc, start_date, end_date, daily_report
        )
        metrics['orders_created'] += validation_stats['created']
        metrics['orders_updated'] += validation_stats['updated']

        # Calculate final statistics
        order_count = len(pos_orders)
        invoice_count = len(pos_invoices)
        
        # Recalculate totals after modifications
        updated_orders = self.search_read(
            [('fiscal_mrc', '=', target_mrc),
             ('date_order', '>=', start_date),
             ('date_order', '<=', end_date),
             ('state', '!=', 'cancel')],
            ['amount_total']
        )
        order_total = sum(order['amount_total'] for order in updated_orders)
        invoice_total = sum(invoice['totalWithTax'] for invoice in pos_invoices)
        
        net_order_total = order_total - refund_total
        net_invoice_total = invoice_total - refund_total
        net_zreport_total = z_sales_total - z_refund_total
        
        # Update daily report
        daily_report.write({
            'pos_order_count': len(updated_orders),
            'invoice_count': invoice_count,
            'refund_count': len(pos_refunds),
            'unmatched_fs_count': validation_stats.get('unmatched', 0),
            'session_total': order_total,
            'z_report_total': z_sales_total,
            'refund_total': refund_total,
            'net_order_total': net_order_total,
            'net_invoice_total': net_invoice_total,
            'zreport_sales_total': z_sales_total,
            'zreport_refund_total': z_refund_total,
            'net_zreport_total': net_zreport_total,
            'total_mismatch': abs(net_order_total - net_zreport_total),
            'recreated_orders': metrics['orders_created'],
            'updated_orders': metrics['orders_updated'],
        })

        # Cancel any posted orders without fiscal data
        cancelled_count = self._cancel_unreconciled_orders(target_mrc, start_date, end_date, daily_report)
        metrics['orders_cancelled'] += cancelled_count
        
        # Update the cancelled orders count in the daily report
        daily_report.write({
            'cancelled_orders': metrics['orders_cancelled']
        })

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Log comprehensive summary
        _logger.info("=" * 60)
        _logger.info("📊 RECONCILIATION SUMMARY")
        _logger.info("=" * 60)
        _logger.info("📦 Orders: %d | Invoices: %d | Refunds: %d", 
                    len(updated_orders), invoice_count, len(pos_refunds))
        _logger.info("💸 Totals - Order: %.2f | Invoice: %.2f | Z-Report: %.2f", 
                    order_total, invoice_total, z_sales_total)
        _logger.info("🔄 Changes - Created: %d | Updated: %d | Cancelled: %d", 
                    metrics['orders_created'], metrics['orders_updated'], metrics['orders_cancelled'])
        _logger.info("🔗 Duplicates: %d found, %d resolved | Orphans linked: %d", 
                    metrics['duplicates_found'], metrics['duplicates_resolved'], metrics['orphans_linked'])
        _logger.info("⏱️ Processing time: %.2f seconds", processing_time)
        _logger.info("=" * 60)

        return {
            'status': 'success',
            'daily_report_id': daily_report.id,
            'metrics': metrics,
            'processing_time': processing_time,
            'order_count': len(updated_orders),
            'invoice_count': invoice_count,
            'order_total': order_total,
            'invoice_total': invoice_total,
            'net_order_total': net_order_total,
            'net_invoice_total': net_invoice_total,
            'net_zreport_total': net_zreport_total,
            'count_match': len(updated_orders) == invoice_count,
            'total_match': abs(net_order_total - net_zreport_total) <= 0.01,
        }

    def _cancel_unreconciled_orders(self, target_mrc, start_date, end_date, daily_report):
        """
        Cancel posted orders that don't have fs_no and mrc after reconciliation.
        
        Args:
            target_mrc (str): The fiscal MRC to check
            start_date (date): Start date for filtering orders
            end_date (date): End date for filtering orders
            daily_report: The daily report object for logging
            
        Returns:
            int: Number of cancelled orders
        """
        _logger.info("🔍 Checking for posted orders without fiscal data after reconciliation...")
        
        # Find posted orders without fs_no and mrc
        unreconciled_orders = self.search([
            ('fiscal_mrc', 'in', [False, '']),
            ('fs_no', 'in', [False, '']),
            ('date_order', '>=', start_date),
            ('date_order', '<=', end_date),
        ])
        _logger.info(start_date)
        _logger.info(unreconciled_orders)
        _logger.info(end_date)
        _logger.info("🔍 Found %d posted orders without fiscal data", len(unreconciled_orders))
        cancelled_count = 0
        for order in unreconciled_orders:
            self._cancel_order(order, "Posted order without fiscal data after reconciliation", daily_report)
            cancelled_count += 1
        
        if cancelled_count > 0:
            _logger.info("❌ Cancelled %d posted orders without fiscal data", cancelled_count)
        else:
            _logger.info("✅ No posted orders without fiscal data found")
            
        return cancelled_count

    def _process_zreports(self, all_zreports, excluded_ids):
        """Process Z-reports with deduplication by date, summing totals."""
        # Filter out excluded Z-reports
        filtered_reports = [z for z in all_zreports if z['id'] not in excluded_ids]

        # Aggregate by date
        date_zreport_map = {}
        for zreport in filtered_reports:
            z_date = zreport['date']
            if z_date not in date_zreport_map:
                # First occurrence — copy all values
                date_zreport_map[z_date] = {
                    'id': zreport['id'],
                    'date': z_date,
                    'salesTotal': zreport.get('salesTotal', 0),
                    'rfdSalesTotal': zreport.get('rfdSalesTotal', 0),
                }
            else:
                # Sum totals, and keep highest ID
                existing = date_zreport_map[z_date]
                existing['salesTotal'] += zreport.get('salesTotal', 0)
                existing['rfdSalesTotal'] += zreport.get('rfdSalesTotal', 0)
                if zreport['id'] > existing['id']:
                    existing['id'] = zreport['id']

                _logger.info(
                    "➕ Summing Z-report for date %s: ID %d (Sales %.2f, Refunds %.2f)",
                    z_date,
                    zreport['id'],
                    zreport.get('salesTotal', 0),
                    zreport.get('rfdSalesTotal', 0)
                )

        return list(date_zreport_map.values())


    def _build_invoice_map(self, invoices):
        """Build comprehensive invoice map with validation."""
        invoice_map = {}
        duplicate_invoices = defaultdict(list)
        
        for inv in invoices:
            fs_number = inv.get('fsNumber')
            if not fs_number:
                _logger.warning("⚠️ Invoice without FS number: ID %s", inv['id'])
                continue
                
            # Standardize FS number format
            fs_key = self._standardize_fs_number(fs_number)
            if not fs_key:
                _logger.warning("⚠️ Invalid FS number format: %s", fs_number)
                continue
            
            if fs_key in invoice_map:
                duplicate_invoices[fs_key].append(inv)
                _logger.warning("⚠️ Duplicate invoice FS %s found, keeping first (ID: %s)", 
                              fs_key, invoice_map[fs_key]['id'])
            else:
                invoice_map[fs_key] = inv
        
        if duplicate_invoices:
            _logger.warning("⚠️ Found %d duplicate invoice FS numbers", len(duplicate_invoices))
        
        return invoice_map

    def _build_order_map(self, orders):
        """Build order map with standardized FS numbers."""
        order_map = {}
        duplicate_orders = defaultdict(list)
        
        for order in orders:
            if order['state'] == 'cancel':
                continue
                
            fs_no = order.get('fs_no')
            if not fs_no:
                continue
                
            fs_key = self._standardize_fs_number(fs_no)
            if not fs_key:
                continue
            
            if fs_key in order_map:
                duplicate_orders[fs_key].append(order)
            else:
                order_map[fs_key] = order
        
        return order_map

    def _standardize_fs_number(self, fs_number):
        """Standardize FS number to integer for consistent comparison."""
        if not fs_number:
            return None
        try:
            # Convert to string, strip whitespace, remove leading zeros
            fs_str = str(fs_number).strip().lstrip('0')
            if not fs_str or not fs_str.isdigit():
                return None
            return int(fs_str)
        except (ValueError, TypeError):
            return None

    def _resolve_duplicate_fs_numbers(self, target_mrc, start_date, end_date, invoice_map, daily_report):
        """
        Enhanced duplicate resolution that:
        1. Finds ALL duplicates with same FS number
        2. Compares each against invoice data
        3. Keeps ONLY the order matching invoice
        4. Cancels all non-matching duplicates
        """
        stats = {'duplicates_found': 0, 'duplicates_resolved': 0, 'orders_cancelled': 0}
        
        # Find all duplicate FS numbers
        groups = self.env['pos.order'].read_group(
            domain=[
                ('fs_no', '!=', False),
                ('fiscal_mrc', '=', target_mrc),
                ('date_order', '>=', start_date),
                ('date_order', '<=', end_date),
                ('state', 'in', ['paid', 'done'])
            ],
            fields=['fs_no'],
            groupby=['fs_no'],
            lazy=False
        )
        
        duplicate_groups = [g for g in groups if g['__count'] > 1]
        stats['duplicates_found'] = len(duplicate_groups)
        
        for dup_group in duplicate_groups:
            fs_no = dup_group['fs_no']
            _logger.info("📋 Processing duplicate FS: %s (Count: %d)", fs_no, dup_group['__count'])
            
            # Get all orders with this FS number
            duplicate_orders = self.env['pos.order'].search([
                ('fs_no', '=', fs_no),
                ('fiscal_mrc', '=', target_mrc),
                ('date_order', '>=', start_date),
                ('date_order', '<=', end_date),
                ('state', 'in', ['paid', 'done'])
            ])
            
            # Find matching invoice
            fs_key = self._standardize_fs_number(fs_no)
            invoice_data = invoice_map.get(fs_key)
            
            if invoice_data:
                # Score each order against invoice
                best_match = self._find_best_matching_order(duplicate_orders, invoice_data)
                
                if best_match:
                    # Keep best match, cancel others
                    for order in duplicate_orders:
                        if order.id != best_match.id:
                            self._cancel_order(order, f"Duplicate of FS {fs_no}, keeping order {best_match.id}", daily_report)
                            stats['orders_cancelled'] += 1
                            stats['duplicates_resolved'] += 1
                    
                    # Update best match to exactly match invoice
                    self._sync_order_with_invoice(best_match, invoice_data, daily_report)
                else:
                    # No good match, cancel all and mark for recreation
                    _logger.warning("⚠️ No matching order for invoice FS %s, cancelling all duplicates", fs_no)
                    for order in duplicate_orders:
                        self._cancel_order(order, f"No match with invoice FS {fs_no}", daily_report)
                        stats['orders_cancelled'] += 1
                    stats['duplicates_resolved'] += 1
            else:
                # No invoice, keep first order only
                _logger.warning("⚠️ No invoice for duplicate FS %s, keeping first order", fs_no)
                for idx, order in enumerate(duplicate_orders):
                    if idx > 0:
                        self._cancel_order(order, f"Duplicate without invoice, FS {fs_no}", daily_report)
                        stats['orders_cancelled'] += 1
                stats['duplicates_resolved'] += 1
        
        return stats

    def _find_best_matching_order(self, orders, invoice_data):
        """Find order that best matches invoice data."""
        best_match = None
        best_score = 0
        
        for order in orders:
            score = 0
            
            # Amount match (highest priority)
            amount_diff = abs(order.amount_total - invoice_data['totalWithTax'])
            if amount_diff < 0.01:
                score += 100  # Exact match
            elif amount_diff < 1.0:
                score += 50   # Close match
            elif amount_diff < 10.0:
                score += 10   # Reasonable match
            
            # Date match
            order_date = order.date_order.date() if hasattr(order.date_order, 'date') else order.date_order
            invoice_date = fields.Date.from_string(invoice_data['date'])
            if order_date == invoice_date:
                score += 20
            
            # Reference number match
            if order.pos_reference and invoice_data.get('referenceNumber'):
                if order.pos_reference == invoice_data['referenceNumber']:
                    score += 30
            
            # Has complete data
            if order.partner_id:
                score += 5
            if order.payment_ids:
                score += 5
            
            if score > best_score:
                best_match = order
                best_score = score
        
        # Only return if score is reasonable
        if best_score >= 50:
            _logger.info("✅ Best match for FS %s: Order %s (score: %d)", 
                        invoice_data['fsNumber'], best_match.id if best_match else None, best_score)
            return best_match
        
        return None

    def _process_orphan_orders(self, target_mrc, start_date, end_date, invoice_map, daily_report):
        """Process orders without fiscal_mrc or fs_no."""
        stats = {'linked': 0, 'cancelled': 0}
        
        orphan_orders = self.with_context(active_test=False).search([
            '|',
            ('fiscal_mrc', '=', False),
            ('fs_no', '=', False),
            ('date_order', '>=', start_date),
            ('date_order', '<=', end_date),
            ('state', 'in', ['paid', 'done']),
        ])
        
        _logger.info("🔍 Found %d orphan orders to process", len(orphan_orders))
        
        for order in orphan_orders:
            matched = False
            
            # Try to match by reference number
            if order.pos_reference:
                for fs_key, inv_data in invoice_map.items():
                    if inv_data.get('referenceNumber') == order.pos_reference:
                        # Link orphan to invoice
                        fs_str = str(fs_key).zfill(8)
                        _logger.info("🔗 Linking orphan order %s to invoice FS %s", order.id, fs_str)
                        
                        order.write({
                            'fiscal_mrc': target_mrc,
                            'fs_no': fs_str,
                        })
                        
                        # Sync with invoice data
                        self._sync_order_with_invoice(order, inv_data, daily_report)
                        
                        self.env['pos.change.log'].log_change(
                            pos_order_id=order.id,
                            fs_no=fs_str,
                            fiscal_mrc=target_mrc,
                            change_type='linked',
                            old_value='orphan',
                            new_value='linked to invoice',
                            daily_report_id=daily_report.id
                        )
                        stats['linked'] += 1
                        matched = True
                        break
            
            # If no match, cancel orphan
            if not matched:
                self._cancel_order(order, "Orphan order without matching invoice", daily_report)
                stats['cancelled'] += 1
        
        return stats

    def _validate_orders_against_invoices(self, invoice_map, order_map, target_mrc, start_date, end_date, daily_report):
        """
        Validate all orders against invoices:
        1. Create orders for unmatched invoices
        2. Update orders with mismatched data
        3. Ensure complete data synchronization
        """
        stats = {'created': 0, 'updated': 0, 'unmatched': 0}
        processed_fs = set()
        
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
                    # Create new order from invoice
                    if self._create_order_from_invoice(invoice_data, target_mrc, daily_report):
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

    def _needs_update(self, order, invoice_data):
        """Check if order needs update from invoice data."""
        # Check 1: Amount difference
        if abs(order.amount_total - invoice_data['totalWithTax']) > 0.01:
            _logger.info("   📊 UPDATE REASON: Amount changed (Order: %.2f, Invoice: %.2f)",
                        order.amount_total, invoice_data['totalWithTax'])
            return True

        # Check 2: Missing important fields
        if not order.fs_no or not order.fiscal_mrc:
            _logger.info("   📊 UPDATE REASON: Missing fiscal data (FS: %s, MRC: %s)",
                        order.fs_no, order.fiscal_mrc)
            return True

        # Check 3: Payment method mismatch
        if invoice_data.get('paymentType') and order.payment_ids:
            payment = order.payment_ids[0]
            if payment.payment_method_id.name != invoice_data['paymentType']:
                _logger.info("   📊 UPDATE REASON: Payment method changed (Order: %s, Invoice: %s)",
                            payment.payment_method_id.name, invoice_data['paymentType'])
                return True

        # Check 4: Product list changed (IMPROVED - Check Count AND Details)
        # Get number of invoice lines from the actual invoice record
        try:
            invoice_id = invoice_data.get('id')
            if invoice_id:
                invoice_rec = self.env['pos.invoice'].browse(invoice_id)
                if invoice_rec.exists():
                    invoice_line_count = len(invoice_rec.line_ids)
                    order_line_count = len(order.lines)

                    # Check 4A: Line count changed
                    if invoice_line_count != order_line_count:
                        _logger.info("   📊 UPDATE REASON: Product count changed (Order: %d items, Invoice: %d items)",
                                    order_line_count, invoice_line_count)
                        return True

                    # Check 4B: Product details changed (even if count same)
                    if invoice_line_count > 0 and order_line_count > 0:
                        for idx, (invoice_line, order_line) in enumerate(
                            zip(invoice_rec.line_ids, order.lines)
                        ):
                            # Check if product changed (by PLU code)
                            invoice_plu = invoice_line.pluCode or 'none'
                            order_plu = order_line.product_id.default_code or 'none'

                            if invoice_plu != order_plu and invoice_plu != 'none':
                                _logger.info("   📊 UPDATE REASON: Product changed at line %d (Order PLU: %s, Invoice PLU: %s)",
                                            idx + 1, order_plu, invoice_plu)
                                return True

                            # Check if quantity changed
                            if abs(invoice_line.quantity - order_line.qty) > 0.01:
                                _logger.info("   📊 UPDATE REASON: Quantity changed at line %d (Order: %.2f, Invoice: %.2f)",
                                            idx + 1, order_line.qty, invoice_line.quantity)
                                return True

                            # Check if price changed significantly
                            if abs(invoice_line.price - order_line.price_unit) > 0.01:
                                _logger.info("   📊 UPDATE REASON: Price changed at line %d (Order: %.2f, Invoice: %.2f)",
                                            idx + 1, order_line.price_unit, invoice_line.price)
                                return True
        except Exception as e:
            _logger.warning("   ⚠️ Could not check product details: %s", str(e))

        return False

    def _create_order_from_invoice(self, invoice_data, target_mrc, daily_report):
        """Create a new POS order from invoice data."""
        try:
            if not invoice_data:
                _logger.warning("⚠️ Invalid invoice data provided")
                return False

            # invoice_data is a dictionary from search_read, need to fetch the actual record
            _logger.info("📄 Creating order from invoice data: FS=%s, ID=%s",
                        invoice_data.get('fsNumber'), invoice_data.get('id'))

            # Fetch the actual invoice record (not just the dict)
            invoice_id = invoice_data.get('id')
            if not invoice_id:
                _logger.error("❌ No invoice ID in invoice_data: %s", invoice_data)
                return False

            invoice_obj = self.env['pos.invoice'].browse(invoice_id)
            if not invoice_obj.exists():
                _logger.error("❌ Invoice with ID %s does not exist", invoice_id)
                return False

            _logger.info("✅ Fetched invoice record: %s", invoice_obj.fsNumber)

            # Validate invoice has necessary data
            if not invoice_obj.fsNumber:
                _logger.error("❌ Invoice has no FS number")
                return False

            if not invoice_obj.line_ids:
                _logger.error("❌ Invoice FS %s has no line items", invoice_obj.fsNumber)
                return False

            # Find or create session for invoice date
            _logger.info("🔍 Looking up/creating session for MRC: %s, Date: %s",
                        target_mrc, invoice_obj.date)
            session_obj = self._find_or_create_session(target_mrc, invoice_obj.date)
            if not session_obj:
                _logger.warning("⚠️ Could not find or create session for MRC: %s, Date: %s",
                              target_mrc, invoice_obj.date)
                return False

            # Extract session ID
            session_id = session_obj.id if hasattr(session_obj, 'id') else session_obj
            _logger.info("✅ Session found/created: Name=%s, ID=%s",
                        session_obj.name if hasattr(session_obj, 'name') else 'Unknown', session_id)

            # Prepare order values from invoice
            _logger.info("📝 Preparing order values from invoice FS: %s", invoice_obj.fsNumber)
            order_vals = self._prepare_pos_order_vals(invoice_obj, target_mrc, session_id)
            if not order_vals:
                _logger.warning("⚠️ Could not prepare order values from invoice FS: %s",
                              invoice_obj.fsNumber)
                return False

            _logger.info("✅ Order values prepared. Lines: %d, Partner: %s, Amount: %.2f",
                        len(order_vals.get('lines', [])), order_vals.get('partner_id'),
                        order_vals.get('amount_total', 0))

            # Create the order
            _logger.info("📦 Creating POS Order from Invoice FS No: %s", invoice_obj.fsNumber)
            _logger.info("   - Planned lines to add: %d", len(order_vals.get('lines', [])))

            new_order = self.create(order_vals)

            if not new_order:
                _logger.error("❌ Failed to create POS Order for Invoice FS: %s", invoice_obj.fsNumber)
                return False

            _logger.info("✅ POS Order created successfully: Name=%s, ID=%s, State=%s",
                        new_order.name, new_order.id, new_order.state)

            # CRITICAL: Refresh the order from database
            _logger.info("   💾 Refreshing order from database...")
            new_order.invalidate_recordset()  # Invalidate cache
            new_order = self.browse(new_order.id)  # Refresh from database
            _logger.info("   ✅ Order refreshed from database")

            # CRITICAL: Check if lines were actually saved
            actual_lines = len(new_order.lines)
            planned_lines = len(order_vals.get('lines', []))

            _logger.info("   - FS No: %s, Amount: %.2f, Partner: %s",
                        new_order.fs_no, new_order.amount_total,
                        new_order.partner_id.name if new_order.partner_id else 'None')
            _logger.info("   📊 LINE COUNT CHECK:")
            _logger.info("      Planned: %d lines | Actual: %d lines", planned_lines, actual_lines)

            if actual_lines == 0 and planned_lines > 0:
                _logger.error("      ❌ CRITICAL ERROR: Lines were not saved!")
                _logger.error("      Expected %d lines but order has 0 lines", planned_lines)
                _logger.error("      This is a database/ORM issue with order creation")
            elif actual_lines == planned_lines:
                _logger.info("      ✅ All lines saved correctly")
            else:
                _logger.warning("      ⚠️ Line count mismatch: Expected %d, got %d", planned_lines, actual_lines)

            # Log the creation
            self.env['pos.change.log'].log_change(
                pos_order_id=new_order.id,
                fs_no=str(invoice_obj.fsNumber).zfill(8),
                fiscal_mrc=target_mrc,
                change_type='recreated',
                old_value='no_order',
                new_value=f"order_created: {new_order.name} (Lines: {len(new_order.lines)})",
                daily_report_id=daily_report.id
            )

            # Auto-invoice if configured
            auto_invoice = self.env.context.get('auto_invoice_created', False)
            if auto_invoice:
                _logger.info("🔄 Auto-invoice configured, invoicing order %s", new_order.id)
                self._auto_invoice_order(new_order, invoice_data, target_mrc, daily_report)
            else:
                _logger.info("ℹ️ Auto-invoice not configured for order %s", new_order.id)

            # Create inventory picking if configured
            create_picking = self.env.context.get('create_inventory_picking', False)
            if create_picking:
                _logger.info("📦 Inventory picking configured, creating for order %s", new_order.id)
                self._create_inventory_picking_for_order(new_order, daily_report)
            else:
                _logger.info("ℹ️ Inventory picking not configured for order %s", new_order.id)

            return True

        except Exception as e:
            _logger.error("❌ Error creating order from invoice FS %s: %s",
                         invoice_data.get('fsNumber') if isinstance(invoice_data, dict) else 'unknown', str(e))
            _logger.exception(e)
            return False

    def _sync_order_with_invoice(self, order, invoice_data, daily_report):
        """Synchronize order with complete invoice data and update inventory/accounting."""
        try:
            _logger.info("🔄 Syncing order %s with invoice FS %s", order.id, invoice_data['fsNumber'])

            old_amount = order.amount_total
            old_state = order.state
            amount_changed = abs(old_amount - invoice_data['totalWithTax']) > 0.01

            # Prepare update values
            update_vals = {
                'amount_total': invoice_data['totalWithTax'],
                'amount_tax': invoice_data.get('totalTax', 0.0),
                'amount_paid': invoice_data.get('totalPaid', invoice_data['totalWithTax']),
                'amount_return': invoice_data.get('change', 0.0),
            }

            # Ensure FS number is properly formatted
            if not order.fs_no or order.fs_no != str(invoice_data['fsNumber']).zfill(8):
                update_vals['fs_no'] = str(invoice_data['fsNumber']).zfill(8)

            # Update reference if available
            if invoice_data.get('referenceNumber') and not order.pos_reference:
                update_vals['pos_reference'] = invoice_data['referenceNumber']

            # IMPORTANT: Set order state to 'paid' so it's finalized
            if order.state not in ['paid', 'done', 'invoiced']:
                _logger.info("📝 Setting order %s state from %s to 'paid'", order.id, order.state)
                update_vals['state'] = 'paid'

            # Update order
            _logger.info("💾 Updating order %s with amount: %.2f", order.id, invoice_data['totalWithTax'])
            order.write(update_vals)

            # Update payment method if needed
            if invoice_data.get('paymentType') and order.payment_ids:
                payment_method_id, _, _ = self.env['pos.payment.method'].get_payment_method_id(
                    invoice_data['paymentType'],
                    order.company_id.id,
                    order.session_id.id if order.session_id else None
                )
                if payment_method_id:
                    _logger.info("💳 Updating payment method for order %s", order.id)
                    order.payment_ids[0].write({
                        'payment_method_id': payment_method_id,
                        'amount': invoice_data['totalWithTax']
                    })

            # IMPROVEMENT #2: Update customer/partner if buyer name changed
            if invoice_data.get('buyerName') and invoice_data['buyerName'] != 'Customer':
                invoice_buyer = invoice_data['buyerName']
                current_partner_name = order.partner_id.name if order.partner_id else 'None'

                # Only update if buyer name is different
                if invoice_buyer.lower() != current_partner_name.lower():
                    _logger.info("🧑 Checking customer for order %s", order.id)
                    _logger.info("   Invoice buyer: %s | Current partner: %s", invoice_buyer, current_partner_name)

                    # Try to find partner by name
                    partner = self.env['res.partner'].search([
                        ('name', '=ilike', invoice_buyer)
                    ], limit=1)

                    if partner:
                        _logger.info("   ✅ Found partner: %s (ID: %s)", partner.name, partner.id)
                        order.write({'partner_id': partner.id})
                        _logger.info("   📝 Updated customer for order %s to: %s", order.id, partner.name)
                    else:
                        _logger.warning("   ⚠️ Customer '%s' not found in system", invoice_buyer)
                        _logger.warning("   Order %s keeps current customer: %s", order.id, current_partner_name)

            # STEP 2.5: Update product lines if they changed (FIX FOR ISSUE #1)
            # Now checks BOTH count AND individual line details (product/qty/price)
            try:
                invoice_id = invoice_data.get('id')
                if invoice_id:
                    invoice_rec = self.env['pos.invoice'].browse(invoice_id)
                    if invoice_rec.exists():
                        invoice_line_count = len(invoice_rec.line_ids)
                        order_line_count = len(order.lines)

                        # Check if rebuild is needed (FIX #1: Added detailed check)
                        needs_rebuild = False
                        rebuild_reason = None

                        # Check 1: Line count changed
                        if invoice_line_count != order_line_count:
                            needs_rebuild = True
                            rebuild_reason = f"Count changed: {order_line_count} → {invoice_line_count}"

                        # Check 2: If count same, check individual line details
                        elif invoice_line_count > 0 and order_line_count > 0:
                            for idx, (invoice_line, order_line) in enumerate(
                                zip(invoice_rec.line_ids, order.lines)
                            ):
                                # Check product PLU changed
                                invoice_plu = invoice_line.pluCode or 'none'
                                order_plu = order_line.product_id.default_code or 'none'

                                if invoice_plu != order_plu and invoice_plu != 'none':
                                    needs_rebuild = True
                                    rebuild_reason = f"Product changed at line {idx + 1}: {order_plu} → {invoice_plu}"
                                    break

                                # Check quantity changed
                                if abs(invoice_line.quantity - order_line.qty) > 0.01:
                                    needs_rebuild = True
                                    rebuild_reason = f"Quantity changed at line {idx + 1}: {order_line.qty} → {invoice_line.quantity}"
                                    break

                                # Check price changed
                                if abs(invoice_line.price - order_line.price_unit) > 0.01:
                                    needs_rebuild = True
                                    rebuild_reason = f"Price changed at line {idx + 1}: {order_line.price_unit} → {invoice_line.price}"
                                    break

                        # Trigger rebuild if needed
                        if needs_rebuild:
                            _logger.info("📦 Product list changed - rebuilding order lines")
                            _logger.info("   Reason: %s", rebuild_reason)
                            self._rebuild_order_lines_from_invoice(order, invoice_rec)
                        else:
                            _logger.info("ℹ️ Product lines match invoice - no rebuild needed")
            except Exception as e:
                _logger.warning("⚠️ Could not update product lines: %s", str(e))

            # STEP 3: Create inventory picking if configured (not just on amount change)
            if self.env.context.get('create_inventory_picking', True):
                if not order.picking_ids:
                    _logger.info("📦 Creating inventory picking for synced order %s", order.id)
                    self._create_inventory_picking_for_order(order, daily_report)
                else:
                    _logger.info("ℹ️ Order %s already has %d picking(s), skipping", order.id, len(order.picking_ids))

            # STEP 4: Create invoice if configured and doesn't exist
            if self.env.context.get('auto_invoice_created', True):
                if not order.account_move:
                    _logger.info("📄 Creating invoice for synced order %s", order.id)
                    self._auto_invoice_order(order, invoice_data, order.fiscal_mrc, daily_report)
                else:
                    _logger.info("ℹ️ Order %s already has invoice %s, skipping",
                               order.id, order.account_move.name)

            # Log the change
            self.env['pos.change.log'].log_change(
                pos_order_id=order.id,
                fs_no=str(invoice_data['fsNumber']).zfill(8),
                fiscal_mrc=order.fiscal_mrc,
                change_type='complete_update',
                old_value=f'state: {old_state}, amount: {old_amount:.2f}',
                new_value=f'state: {order.state}, amount: {invoice_data["totalWithTax"]:.2f}',
                daily_report_id=daily_report.id
            )

            _logger.info("✅ Synced order %s: State=%s, Amount=%.2f, Has Invoice=%s, Has Picking=%s",
                        order.id, order.state, order.amount_total,
                        order.account_move.name if order.account_move else 'No',
                        len(order.picking_ids) if order.picking_ids else 'No')

        except Exception as e:
            _logger.error("❌ Failed to sync order %s: %s", order.id, str(e))
            _logger.exception(e)

    def _rebuild_order_lines_from_invoice(self, order, invoice_rec):
        """Rebuild all order lines from invoice lines when product list changes."""
        try:
            _logger.info("📋 Rebuilding order lines from invoice FS: %s", invoice_rec.fsNumber)

            # FIX: Save original state before deleting lines
            # Odoo prevents unlinking order lines from paid/done orders
            original_state = order.state
            _logger.info("   📝 Current order state: %s", original_state)

            # If order is paid/done, temporarily set to draft to allow line deletion
            if original_state not in ['new', 'cancelled']:
                _logger.info("   🔄 Temporarily changing order state from %s to 'draft' to allow line deletion", original_state)
                order.write({'state': 'draft'})

            # Delete all existing order lines
            old_line_count = len(order.lines)
            _logger.info("   🗑️ Deleting %d existing order lines", old_line_count)
            try:
                order.lines.unlink()
                _logger.info("   ✅ Successfully deleted %d lines", old_line_count)
            except Exception as unlink_error:
                _logger.error("   ❌ Error deleting lines: %s", str(unlink_error))
                # Restore original state before raising error
                if original_state not in ['new', 'cancelled']:
                    order.write({'state': original_state})
                raise

            # IMPROVEMENT #4: Cancel existing pickings before rebuilding to prevent double inventory movements
            if order.picking_ids:
                _logger.info("📦 IMPROVEMENT #4: Cancelling %d existing picking(s) before product update", len(order.picking_ids))
                for picking in order.picking_ids:
                    if picking.state not in ['done', 'cancel']:
                        picking_name = picking.name
                        picking.action_cancel()
                        _logger.info("   ✅ Cancelled picking: %s (state was %s)", picking_name, picking.state)
                    else:
                        _logger.info("   ℹ️ Skipping picking %s (already %s)", picking.name, picking.state)
            else:
                _logger.info("   ℹ️ No existing pickings to cancel")

            # Rebuild product list using same logic as order creation
            company_id = order.company_id.id
            order_lines = []
            products_found = 0
            products_missing = 0

            for idx, line in enumerate(invoice_rec.line_ids):
                if not line.itemName:
                    _logger.warning("   [Line %d] Skipping - no item name", idx + 1)
                    continue

                # Product lookup (same strategy as in _prepare_pos_order_vals)
                product = None

                # Try by PLU code
                if line.pluCode and line.pluCode != '0000':
                    product = self.env['product.product'].search([
                        ('default_code', '=', line.pluCode)
                    ], limit=1)
                    if product:
                        _logger.info("   [Line %d] Found by PLU: %s", idx + 1, line.pluCode)

                # Try by exact name match
                if not product and line.itemName:
                    product = self.env['product.product'].search([
                        ('name', '=ilike', line.itemName)
                    ], limit=1)
                    if product:
                        _logger.info("   [Line %d] Found by exact name: %s", idx + 1, line.itemName)

                # Try partial match (each word)
                if not product and line.itemName:
                    words = line.itemName.split()
                    for word in words:
                        if len(word) > 3:  # Only try words longer than 3 chars
                            product = self.env['product.product'].search([
                                ('name', 'ilike', word)
                            ], limit=1)
                            if product:
                                _logger.info("   [Line %d] Found by partial word '%s': %s", idx + 1, word, product.name)
                                break

                # Fallback: Try to find ANY product with similar name using contains
                if not product and line.itemName:
                    # Extract first word only
                    first_word = line.itemName.split()[0] if line.itemName else ""
                    if first_word:
                        product = self.env['product.product'].search([
                            ('name', 'ilike', f'%{first_word}%')
                        ], limit=1)
                        if product:
                            _logger.info("   [Line %d] Found by contains first word '%s': %s", idx + 1, first_word, product.name)

                # IMPROVEMENT #3: No fallback - RAISE ERROR instead
                if not product:
                    _logger.error("   [Line %d] ❌ CRITICAL: No product found anywhere for: '%s' (PLU: %s)",
                                idx + 1, line.itemName, line.pluCode)
                    _logger.error("      Tried:")
                    _logger.error("        1. PLU code exact match: %s", line.pluCode)
                    _logger.error("        2. Exact product name match: %s", line.itemName)
                    _logger.error("        3. Partial word match")
                    _logger.error("        4. Contains match with first word")
                    _logger.error("")
                    _logger.error("      Available actions to fix this:")
                    _logger.error("        1. Add product to Odoo with PLU code: %s", line.pluCode)
                    _logger.error("        2. Update PLU code in fiscal printer to match Odoo product")
                    _logger.error("        3. Configure product mapping if name differs")
                    _logger.error("")

                    # RAISE ERROR to force resolution
                    error_msg = (
                        f"Product matching failed for line {idx + 1}: "
                        f"'{line.itemName}' (PLU: {line.pluCode})\n"
                        f"This line cannot be processed without a valid product. "
                        f"Please add the product to Odoo or fix the PLU code in the fiscal printer."
                    )
                    _logger.error("   🚫 %s", error_msg)
                    raise ValueError(error_msg)

                products_found += 1

                # Tax lookup
                tax_id = False
                if line.taxRate:
                    tax = self.env['account.tax'].search([
                        ('amount', '=', line.taxRate)
                    ], limit=1)
                    if not tax:
                        tax = self.env['account.tax'].search([
                            ('amount', '>=', line.taxRate - 0.1),
                            ('amount', '<=', line.taxRate + 0.1)
                        ], limit=1)
                    if tax:
                        tax_id = tax.id

                # Add to order lines with matched product
                _logger.info("   ✅ [Line %d] Added: %s x %.2f @ %.2f (Tax: %.2f%%)",
                           idx + 1, product.name, line.quantity, line.price, line.taxRate)
                order_lines.append((0, 0, {
                    'product_id': product.id,
                    'full_product_name': product.name or line.itemName,
                    'qty': line.quantity,
                    'price_unit': line.price,
                    'price_subtotal': line.lineTotal,
                    'price_subtotal_incl': line.lineTotalWithTax,
                    'tax_ids': [(6, 0, [tax_id])] if tax_id else [],
                }))

            # Update order with new lines
            if order_lines:
                _logger.info("   📝 Attempting to write %d lines to order %s", len(order_lines), order.id)

                try:
                    # Try batch write first
                    order.write({'lines': order_lines})

                    # Verify lines were created
                    updated_order = order.browse(order.id)
                    actual_line_count = len(updated_order.lines)

                    if actual_line_count == len(order_lines):
                        _logger.info("   ✅ Rebuilt order lines: %d added (%d missing products)",
                                   products_found, products_missing)
                    else:
                        _logger.warning("   ⚠️ Line count mismatch! Expected %d, got %d. Attempting one-by-one insertion.",
                                      len(order_lines), actual_line_count)
                        # Fallback: Create lines one by one
                        self._create_order_lines_fallback(order, order_lines)

                except Exception as write_error:
                    _logger.error("   ❌ Batch write failed: %s. Attempting one-by-one insertion.", str(write_error))
                    _logger.exception(write_error)
                    # Fallback: Create lines one by one
                    try:
                        self._create_order_lines_fallback(order, order_lines)
                    except Exception as fallback_error:
                        _logger.error("   ❌ Fallback creation also failed: %s", str(fallback_error))
                        _logger.exception(fallback_error)
            else:
                _logger.warning("   ⚠️ No valid lines to rebuild!")

            # IMPROVEMENT #4: Create new picking with the rebuilt lines to ensure inventory is correct
            # This is essential after canceling old pickings - we need new ones with the correct products
            if order.lines and not order.picking_ids:
                _logger.info("📦 Creating new picking with rebuilt product lines")
                try:
                    # Get daily report for picking creation
                    daily_report = None
                    if order.session_id and order.session_id.daily_report_id:
                        daily_report = order.session_id.daily_report_id

                    self._create_inventory_picking_for_order(order, daily_report)
                    _logger.info("   ✅ New picking created successfully with %d lines", len(order.lines))
                except Exception as picking_error:
                    _logger.warning("   ⚠️ Could not create new picking after rebuild: %s", str(picking_error))
                    # Don't fail the rebuild if picking creation fails - lines are already updated

            # FIX: Restore original order state if it was temporarily changed
            if original_state not in ['new', 'cancelled']:
                _logger.info("   🔄 Restoring order state from 'draft' back to original state: %s", original_state)
                order.write({'state': original_state})
                _logger.info("   ✅ Order state restored to: %s", original_state)

        except Exception as e:
            _logger.error("❌ Failed to rebuild order lines for order %s: %s", order.id, str(e))
            _logger.exception(e)
            # Make sure to restore state even if there's an error
            try:
                if original_state not in ['new', 'cancelled']:
                    order.write({'state': original_state})
                    _logger.info("   ✅ Order state restored to: %s (after error)", original_state)
            except Exception as restore_error:
                _logger.warning("   ⚠️ Could not restore order state: %s", str(restore_error))

    def _create_order_lines_fallback(self, order, order_lines):
        """Fallback: Create order lines one-by-one if batch write fails."""
        _logger.info("   🔄 [FALLBACK] Creating %d lines one-by-one", len(order_lines))

        pos_order_line_model = self.env['pos.order.line']
        created_count = 0
        failed_count = 0

        for idx, line_data in enumerate(order_lines):
            try:
                # Extract the actual line data from the (0, 0, {...}) tuple
                _, _, line_vals = line_data

                # Ensure we have product_id - this is REQUIRED
                if not line_vals.get('product_id'):
                    _logger.warning("   ⚠️ [Line %d] Skipping - no product_id", idx + 1)
                    failed_count += 1
                    continue

                # Add order reference
                line_vals['order_id'] = order.id

                # Create the line
                created_line = pos_order_line_model.create(line_vals)
                created_count += 1

                _logger.info("   ✅ [Line %d] Created: %s x %.2f",
                           idx + 1,
                           created_line.product_id.name,
                           created_line.qty)

            except Exception as line_error:
                failed_count += 1
                _logger.error("   ❌ [Line %d] Failed to create: %s", idx + 1, str(line_error))

        _logger.info("   📊 Fallback result: %d created, %d failed out of %d",
                   created_count, failed_count, len(order_lines))

        if failed_count == 0:
            _logger.info("   ✅ All fallback lines created successfully!")
        else:
            _logger.warning("   ⚠️ Some fallback lines failed to create")

    def _create_inventory_picking_for_order(self, order, daily_report):
        """
        Create inventory picking for order after invoice synchronization.
        Fully prevents double deduction and respects session's stock configuration.
        Forces picking creation by temporarily overriding session stock settings.
        """
        try:
            _logger.info("📦 Evaluating inventory picking for order %s (FS: %s, State: %s)", order.id, order.fs_no, order.state)

            # Check if order has storable products
            storable_lines = order.lines.filtered(
                lambda l: l.product_id.type in ['product', 'consu'] and l.qty > 0
            )

            if not storable_lines:
                _logger.info("ℹ️ Order %s has no storable items — no picking required", order.id)
                return

            # Prevent double picking creation
            if order.picking_ids:
                _logger.warning(
                    "⚠️ Picking already exists for order %s (count: %d). Skipping to prevent double deduction.",
                    order.id, len(order.picking_ids)
                )
                return

            # Ensure order is in correct state for picking creation
            _logger.info("📝 Order %s current state: %s", order.id, order.state)
            if order.state not in ['paid', 'done', 'invoiced']:
                _logger.warning("⚠️ Order %s is in %s state. Setting to 'done' for picking creation.", order.id, order.state)
                order.write({'state': 'done'})

            # Get session and save original stock setting
            session = order.session_id
            if not session:
                _logger.error("❌ Order %s has no session. Cannot create picking.", order.id)
                return

            original_update_stock = session.update_stock_at_closing

            try:
                # Check if picking already exists (created by Odoo during order.create)
                order.invalidate_recordset(['picking_ids'])

                if order.picking_ids:
                    _logger.info("✅ Picking already created by Odoo for order %s", order.id)
                    _logger.info("   Existing pickings: %s", [p.name for p in order.picking_ids])
                    picking_result = order.picking_ids
                else:
                    # No picking exists, create one manually
                    _logger.info("📦 No picking found, creating manually for order %s", order.id)

                    # Force picking creation by disabling stock update at closing
                    _logger.info("   📦 Temporarily overriding session stock setting")
                    session.write({'update_stock_at_closing': False})

                    _logger.info("   📦 Calling order._create_order_picking()")
                    picking_result = order._create_order_picking()
                    _logger.info("   📦 _create_order_picking() returned: %s", picking_result)

            except Exception as picking_error:
                _logger.error("❌ Error during picking creation: %s", str(picking_error))
                _logger.exception(picking_error)
                raise
            finally:
                # Restore original session setting
                _logger.info("📝 Restoring session stock setting for order %s", order.id)
                session.write({'update_stock_at_closing': original_update_stock})

            # Refresh and check if pickings were created
            order.invalidate_recordset(['picking_ids'])
            _logger.info("📋 After picking creation - Order %s has %d picking(s)", order.id, len(order.picking_ids))

            if order.picking_ids:
                _logger.info("✅ Successfully created %d picking(s) for order %s", len(order.picking_ids), order.id)
                for picking in order.picking_ids:
                    _logger.info("   - Picking: %s (State: %s, ID: %s)", picking.name, picking.state, picking.id)

                # Log picking creation
                self.env['pos.change.log'].log_change(
                    pos_order_id=order.id,
                    fs_no=order.fs_no,
                    fiscal_mrc=order.fiscal_mrc,
                    change_type='inventory_picking_created',
                    old_value='no_picking',
                    new_value=f'{len(order.picking_ids)} picking(s) created: {", ".join([p.name for p in order.picking_ids])}',
                    daily_report_id=daily_report.id
                )
            else:
                _logger.warning("⚠️ No pickings created for order %s despite session override", order.id)

        except Exception as e:
            _logger.error("❌ Failed to create picking for order %s: %s", order.id, str(e))
            _logger.exception(e)

    def _handle_move_rounding_tolerance(self, move, tolerance=0.05):
        """Handle minor rounding differences in journal entries.

        When calculating line totals with different tax rates, small decimal
        differences can accumulate (e.g., 18,751.33 debit vs 18,751.31 credit).

        This method:
        1. Checks if the move is balanced
        2. If difference < tolerance, adds rounding adjustment line
        3. If difference >= tolerance, raises error

        Args:
            move: account.move record
            tolerance: Maximum allowed difference (default 0.05)

        Returns:
            True if balanced or fixed, False if error
        """
        if not move or not move.line_ids:
            return True

        # Calculate totals
        total_debit = sum(move.line_ids.mapped('debit'))
        total_credit = sum(move.line_ids.mapped('credit'))
        difference = abs(total_debit - total_credit)

        _logger.info("💰 Move balance check: Debit=%.2f, Credit=%.2f, Diff=%.2f",
                    total_debit, total_credit, difference)

        # Already balanced
        if difference < 0.001:  # Essentially zero
            _logger.info("✅ Move is balanced")
            return True

        # Difference within tolerance
        if difference <= tolerance:
            _logger.warning("⚠️ Move has minor rounding difference: %.2f (within tolerance %.2f)",
                           difference, tolerance)

            # Add rounding adjustment to balance
            rounding_account_id = False

            # Try to find or create rounding account
            rounding_accounts = self.env['account.account'].search([
                ('code', '=', 'ROUNDING'),
                ('company_id', '=', move.company_id.id)
            ])

            if rounding_accounts:
                rounding_account_id = rounding_accounts[0].id
            else:
                # Fallback: use miscellaneous account if rounding doesn't exist
                misc_accounts = self.env['account.account'].search([
                    ('name', 'ilike', 'Rounding'),
                    ('company_id', '=', move.company_id.id)
                ], limit=1)
                if misc_accounts:
                    rounding_account_id = misc_accounts[0].id

            if rounding_account_id:
                # Add line to balance the move
                if total_debit > total_credit:
                    # Credit is less, add credit line
                    self.env['account.move.line'].create({
                        'move_id': move.id,
                        'account_id': rounding_account_id,
                        'credit': round(difference, 2),
                        'debit': 0.0,
                        'name': f'Rounding adjustment ({difference:.2f})',
                    })
                    _logger.info("✅ Added rounding adjustment credit: %.2f", difference)
                else:
                    # Debit is less, add debit line
                    self.env['account.move.line'].create({
                        'move_id': move.id,
                        'account_id': rounding_account_id,
                        'debit': round(difference, 2),
                        'credit': 0.0,
                        'name': f'Rounding adjustment ({difference:.2f})',
                    })
                    _logger.info("✅ Added rounding adjustment debit: %.2f", difference)

                # Revalidate
                move.invalidate_recordset()
                total_debit = sum(move.line_ids.mapped('debit'))
                total_credit = sum(move.line_ids.mapped('credit'))
                final_diff = abs(total_debit - total_credit)
                _logger.info("✅ After adjustment: Debit=%.2f, Credit=%.2f, Diff=%.2f",
                           total_debit, total_credit, final_diff)
                return True
            else:
                _logger.warning("⚠️ No rounding account found, but difference within tolerance")
                return True  # Allow it anyway since within tolerance

        # Difference too large
        _logger.error("❌ Move is NOT balanced - difference %.2f exceeds tolerance %.2f",
                     difference, tolerance)
        return False

    def _auto_invoice_order(self, order, invoice_data, target_mrc, daily_report):
        """Auto-invoice order with proper state management and detailed error handling."""
        _logger.info("🔄 Auto-invoicing order FS No: %s (ID: %s, State: %s)",
                    invoice_data['fsNumber'], order.id, order.state)
        try:
            # PRE-CHECK: Log lines before any modifications
            _logger.info("   📊 PRE-CHECK - Order lines before invoicing: %d lines", len(order.lines))
            for idx, line in enumerate(order.lines):
                _logger.info("      [Line %d] %s x %.2f @ %.2f",
                           idx + 1, line.product_id.name if line.product_id else 'NO PRODUCT',
                           line.qty, line.price_unit)

            # Validation checks
            if not order.partner_id:
                _logger.warning("⚠️ Order %s has no partner, cannot invoice", order.id)
                return

            if not order.lines:
                _logger.warning("⚠️ Order %s has no lines, cannot invoice", order.id)
                return

            # Ensure order is in invoiceable state
            _logger.info("📝 Order state before invoicing: %s", order.state)
            if order.state not in ['paid', 'done', 'invoiced']:
                _logger.info("📝 Setting order %s to 'done' state for invoicing", order.id)
                order.write({'state': 'done'})
                _logger.info("   📊 Lines after state change: %d lines", len(order.lines))

            # Set to_invoice flag
            _logger.info("📝 Setting to_invoice flag for order %s", order.id)
            order.write({'to_invoice': True})
            _logger.info("   📊 Lines after to_invoice flag: %d lines", len(order.lines))

            # CRITICAL: Flush pending updates before proceeding
            _logger.info("💾 Flushing pending updates before invoicing...")
            self.env.flush_all()
            _logger.info("   ✅ Updates flushed")

            # CRITICAL: Refresh order from database first
            _logger.info("📄 Refreshing order %s from database before invoicing...", order.id)
            order.invalidate_recordset()
            order = self.browse(order.id)
            _logger.info("   ✅ Order refreshed, verifying lines: %d lines", len(order.lines))

            # CRITICAL: Save lines BEFORE invoicing (action_pos_order_invoice deletes them)
            _logger.info("📄 Saving order lines BEFORE invoicing...")
            lines_backup = []
            for idx, line in enumerate(order.lines):
                lines_backup.append({
                    'product_id': line.product_id.id if line.product_id else False,
                    'qty': line.qty,
                    'price_unit': line.price_unit,
                    'full_product_name': line.full_product_name,
                    'tax_ids': [(6, 0, [t.id for t in line.tax_ids])] if line.tax_ids else [],
                    'price_subtotal': line.price_subtotal,
                    'price_subtotal_incl': line.price_subtotal_incl,
                })
                _logger.info("      [Backup %d] %s x %.2f", idx + 1, line.full_product_name, line.qty)
            _logger.info("   💾 Backed up %d lines", len(lines_backup))

            # Create invoice using Odoo's standard method
            _logger.info("📄 Calling action_pos_order_invoice() for order %s", order.id)
            _logger.info("   📊 Lines BEFORE action_pos_order_invoice(): %d lines", len(order.lines))

            try:
                invoice_result = order.action_pos_order_invoice()
                _logger.info("📄 action_pos_order_invoice() returned: %s", type(invoice_result).__name__)
            except Exception as invoice_error:
                _logger.error("❌ ERROR during action_pos_order_invoice(): %s", str(invoice_error))
                _logger.exception(invoice_error)
                raise

            # POST-CHECK: Check lines after invoice creation
            _logger.info("   📊 Lines AFTER action_pos_order_invoice(): %d lines", len(order.lines))
            if len(order.lines) == 0 and len(lines_backup) > 0:
                _logger.error("   ❌ action_pos_order_invoice() DELETED the lines! Restoring from backup...")

                # Restore the lines
                for line_data in lines_backup:
                    try:
                        self.env['pos.order.line'].create({
                            'order_id': order.id,
                            **line_data
                        })
                        _logger.info("   ✅ Restored line: %s x %.2f",
                                   line_data.get('full_product_name', 'Unknown'),
                                   line_data['qty'])
                    except Exception as restore_error:
                        _logger.error("   ❌ Failed to restore line: %s", str(restore_error))

                # Verify lines were restored
                _logger.info("   📊 After restoration: %d lines", len(order.lines))

                # Flush restored lines to database
                _logger.info("💾 Flushing restored lines to database...")
                self.env.flush_all()
                _logger.info("   ✅ Restored lines flushed")

            # Refresh order to get latest data
            _logger.info("🔄 Refreshing order to get latest data...")
            order.invalidate_recordset()
            order = self.browse(order.id)
            _logger.info("   ✅ Order refreshed, final line count: %d lines", len(order.lines))

            # Verify invoice was created
            if order.account_move:
                _logger.info("✅ Account move created successfully: %s (State: %s, ID: %s)",
                           order.account_move.name, order.account_move.state, order.account_move.id)

                # CRITICAL: Check and fix rounding tolerance (difference < 0.05)
                _logger.info("🔍 Checking move balance with rounding tolerance...")
                if self._handle_move_rounding_tolerance(order.account_move, tolerance=0.05):
                    _logger.info("✅ Move is balanced (or fixed with rounding adjustment)")
                else:
                    _logger.error("❌ Move cannot be balanced - difference too large")

                # Log auto-invoicing
                self.env['pos.change.log'].log_change(
                    pos_order_id=order.id,
                    fs_no=str(invoice_data['fsNumber']).zfill(8),
                    fiscal_mrc=target_mrc,
                    change_type='auto_invoiced',
                    old_value='no_invoice',
                    new_value=f"invoiced: {order.account_move.name} (State: {order.account_move.state})",
                    daily_report_id=daily_report.id
                )
            else:
                _logger.warning("⚠️ Invoice creation returned no account_move for order %s", order.id)

        except Exception as e:
            error_msg = str(e)
            _logger.error("❌ Failed to invoice order FS No: %s (Order ID: %s) due to: %s",
                         invoice_data['fsNumber'], order.id, error_msg)
            _logger.exception(e)

            # If it's an accounting error (unbalanced move), try to fix with rounding tolerance
            if "not balanced" in error_msg.lower():
                _logger.warning("⚠️ Order FS No: %s has unbalanced move, attempting rounding tolerance fix",
                               invoice_data['fsNumber'])
                if order.account_move:
                    if self._handle_move_rounding_tolerance(order.account_move, tolerance=0.05):
                        _logger.info("✅ Move fixed with rounding tolerance")
                    else:
                        _logger.error("❌ Move still unbalanced after rounding tolerance check")
                _logger.warning("   Continuing reconciliation - order may need manual invoice creation")
            else:
                _logger.error("ℹ️ Order FS No: %s created but invoicing failed - may need manual review",
                             invoice_data['fsNumber'])

    def _find_or_create_session(self, target_mrc, date):
        """Find existing session for the date."""
        _logger.info("🔍 [Session Lookup] Starting session search for MRC: %s, Date: %s", target_mrc, date)
        
        # First, try to find any order from the same day and get its session
        order_date = fields.Datetime.to_datetime(date).date()
        date_start = fields.Datetime.to_datetime(date).replace(hour=0, minute=0, second=0)
        date_end = fields.Datetime.to_datetime(date).replace(hour=23, minute=59, second=59)
        
        _logger.info("🔍 [Session Lookup] Searching for orders between %s and %s", date_start, date_end)
        
        order = self.env['pos.order'].search([
            ('fiscal_mrc', '=', target_mrc),
            ('date_order', '>=', date_start),
            ('date_order', '<=', date_end),
            ('session_id', '!=', False)
        ], limit=1, order='date_order asc')
        
        if order and order.session_id:
            _logger.info("✅ [Session Lookup] Found order #%s with session ID: %s", order.id, order.session_id.id)
            return order.session_id
        else:
            _logger.info("ℹ️ [Session Lookup] No suitable order found with session, checking for active sessions...")
            
        # If no order found, try to find an existing session for the date range
        sessions = self.env['pos.session'].with_context(active_test=False).search([
            ('start_at', '<=', date),
            ('stop_at', '>=', date),
            ('order_ids.fiscal_mrc', '=', target_mrc)
        ], limit=1)
        
        if sessions:
            _logger.info("✅ [Session Lookup] Found active session: %s (ID: %s)", sessions.name, sessions.id)
        else:
            _logger.warning("⚠️ [Session Lookup] No active session found for MRC %s on %s", target_mrc, date)
            
        return sessions

    def _cancel_order(self, order, reason, daily_report):
        """Cancel an order with proper logging."""
        try:
            _logger.info("❌ Cancelling order %s: %s", order.id, reason)
            
            if hasattr(order, 'action_cancel'):
                order.action_cancel()
            else:
                order.write({'state': 'cancel'})
            
            # Log cancellation
            self.env['pos.change.log'].log_change(
                pos_order_id=order.id,
                fs_no=order.fs_no or 'N/A',
                fiscal_mrc=order.fiscal_mrc or 'N/A',
                change_type='cancelled',
                old_value=f'state: {order.state}',
                new_value=f'cancelled: {reason}',
                daily_report_id=daily_report.id
            )
            
        except Exception as e:
            _logger.error("❌ Failed to cancel order %s: %s", order.id, str(e))

    def _parse_table_from_header(self, header_memo):
        """Extract only table name from header memo"""
        if not header_memo:
            return None
        
        lines = header_memo.strip().split('\n')
        for line in lines:
            if 'Table' in line:
                return line.split(':')[-1].strip()
        
        return None

    def _get_table_id(self, table_name, session_id):
        """Get table by name or return first available table"""
        session = self.env['pos.session'].browse(session_id)
        config_id = session.config_id.id if session else None
        
        # Get floors for this POS config
        floors = self.env['restaurant.floor'].search([
            ('pos_config_ids', 'in', [config_id])
        ])
        floor_ids = floors.ids
        
        if table_name and table_name != 'Takeaway' and floor_ids:
            # Try to find table by name
            table = self.env['restaurant.table'].search([
                ('name', '=ilike', table_name),
                ('floor_id', 'in', floor_ids)
            ], limit=1)
            if table:
                _logger.info(f"✅ Found table: {table.name} (ID={table.id})")
                return table.id
        
        # If no match or Takeaway, get first available table
        if floor_ids:
            first_table = self.env['restaurant.table'].search([
                ('floor_id', 'in', floor_ids)
            ], limit=1)
            
            if first_table:
                _logger.info(f"✅ Using first available table: {first_table.name} (ID={first_table.id})")
                return first_table.id
        
        # Default: return table ID 1
        _logger.warning(f"⚠️ No table found, using default table ID=1")
        return 1

    def _combine_date_time(self, invoice_date, invoice_time):
        """Combine date and time fields from invoice"""
        if not invoice_time:
            return invoice_date
        
        try:
            # Parse time string (format: "HH:MM:SS")
            time_parts = invoice_time.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            second = int(time_parts[2]) if len(time_parts) > 2 else 0
            
            # Combine with date
            datetime_combined = fields.Datetime.to_datetime(invoice_date)
            datetime_combined = datetime_combined.replace(
                hour=hour, 
                minute=minute, 
                second=second
            )
            return datetime_combined
        except:
            return invoice_date

    def _prepare_pos_order_vals(self, invoice, fiscal_mrc, session_id):
        """Prepare order values from invoice with complete data mapping."""
        _logger.info("📝 [START] Preparing order values for invoice FS: %s", invoice.fsNumber)

        company_id = self.env.company.id

        # Handle both session object and session ID
        if isinstance(session_id, int):
            session = self.env['pos.session'].browse(session_id)
        else:
            session = session_id

        if not session or not session.exists():
            _logger.error("❌ Invalid session: %s", session_id)
            return False

        session_id = session.id  # Ensure we have the numeric ID
        _logger.info("✅ Session found: %s (Config: %s, ID: %s)", session.name, session.config_id.name, session_id)

        # Get payment method - MUST be from session's available methods
        _logger.info("💳 Looking up payment method: %s (for session %s)",
                    invoice.paymentType or 'Cash', session.id)

        # Get session's available payment methods
        available_methods = session.config_id.payment_method_ids
        _logger.info("   Available payment methods in session: %s",
                    [f"{m.name} (ID: {m.id})" for m in available_methods])

        payment_method_id = None

        # Try to find payment method by invoice type
        if invoice.paymentType:
            for method in available_methods:
                if method.name.lower() == invoice.paymentType.lower():
                    payment_method_id = method.id
                    _logger.info("   ✅ Found exact match: %s (ID: %s)", method.name, method.id)
                    break

        # If not found, try case-insensitive partial match
        if not payment_method_id and invoice.paymentType:
            invoice_type_lower = invoice.paymentType.lower()
            for method in available_methods:
                if invoice_type_lower in method.name.lower():
                    payment_method_id = method.id
                    _logger.info("   ✅ Found partial match: %s (ID: %s)", method.name, method.id)
                    break

        # If still not found, use first "Cash" method or first available method
        if not payment_method_id:
            _logger.warning("   ⚠️ Payment type '%s' not found, looking for fallback...", invoice.paymentType)

            # Try to find "Cash" payment method
            cash_method = next((m for m in available_methods if 'cash' in m.name.lower()), None)
            if cash_method:
                payment_method_id = cash_method.id
                _logger.info("   ✅ Using fallback 'Cash' method: %s (ID: %s)", cash_method.name, cash_method.id)
            elif available_methods:
                # Use the first available method
                payment_method_id = available_methods[0].id
                _logger.warning("   ⚠️ Using first available method: %s (ID: %s)",
                              available_methods[0].name, available_methods[0].id)

        if not payment_method_id:
            _logger.error("❌ No payment method available in session %s for invoice FS %s",
                         session.id, invoice.fsNumber)
            return False

        _logger.info("✅ Final payment method selected: ID=%s", payment_method_id)

        # Partner lookup
        _logger.info("👤 Looking up partner: %s", invoice.buyerName or 'None')
        partner_id = False
        if invoice.buyerName and invoice.buyerName != "Customer":
            partner = self.env['res.partner'].search([('name', '=ilike', invoice.buyerName)], limit=1)
            if partner:
                partner_id = partner.id
                _logger.info("✅ Found partner: %s (ID: %s)", partner.name, partner_id)

        # Set default partner if not found (starts with 'walk' or specific customer ID)
        if not partner_id:
            _logger.info("ℹ️ No partner found for buyer name '%s', looking for default...", invoice.buyerName)
            # First try to find a partner starting with 'walk'
            default_partner = self.env['res.partner'].search([('name', '=ilike', 'walk%')], limit=1)
            if not default_partner:
                # If no 'walk' partner found, use the specific customer with ID 1
                _logger.info("ℹ️ No 'walk' partner found, checking default customer ID 1")
                default_partner = self.env['res.partner'].browse(1).exists()

            if default_partner:
                partner_id = default_partner.id
                _logger.info("✅ Using default partner: %s (ID: %s)", default_partner.name, partner_id)
            else:
                _logger.warning("⚠️ No default partner found - order will have no partner!")

        # Employee lookup
        employee_id = False
        if invoice.cashierName:
            employee = self.env['hr.employee'].search([('name', '=ilike', invoice.cashierName)], limit=1)
            if employee:
                employee_id = employee.id
        
        company_id = invoice.device_id.company_id.id if invoice.device_id else self.env.company.id

        # Extract table from headerMemo
        table_name = self._parse_table_from_header(invoice.headerMemo)
        table_id = self._get_table_id(table_name, session_id)
        
        # Combine date and time for accurate order datetime
        order_datetime = self._combine_date_time(invoice.date, invoice.time)

        # Prepare order lines
        line_count = len(invoice.line_ids) if invoice.line_ids else 0
        _logger.info("📦 [CRITICAL CHECK] Processing invoice lines for FS %s", invoice.fsNumber)
        _logger.info("   - Invoice ID: %s", invoice.id)
        _logger.info("   - Reference: %s", invoice.referenceNumber or 'None')
        _logger.info("   - Total Amount: %.2f", invoice.totalWithTax)
        _logger.info("   - Line count: %d", line_count)

        if line_count == 0:
            _logger.error("   ❌ CRITICAL: Invoice has NO LINE ITEMS!")
            _logger.error("   This is why products aren't appearing in the order.")
            _logger.error("   Check if invoice.line_ids exists or if data is missing from invoice record.")

        order_lines = []
        for idx, line in enumerate(invoice.line_ids):
            _logger.info("   [Line %d/%d] Item: %s, PLU: %s, Qty: %.2f",
                        idx + 1, len(invoice.line_ids), line.itemName, line.pluCode, line.quantity)

            if not line.itemName:
                _logger.warning("   ⚠️ Skipping line %d - no item name", idx + 1)
                continue

            # Product lookup with better matching (from backup version)
            product = None
            _logger.info("   🔍 Searching for product: '%s' (PLU: %s)", line.itemName, line.pluCode)

            # First priority: PLU code exact match (company-specific or shared)
            if line.pluCode and line.pluCode != '0000':
                product = self.env['product.product'].search([
                    ('default_code', '=', line.pluCode),
                    ('company_id', 'in', [company_id, False])  # Company specific or shared
                ], limit=1)
                if product:
                    _logger.info("   ✅ Found product by PLU code: %s", product.name)

            # Second priority: Exact name match
            if not product and line.itemName:
                product = self.env['product.product'].search([
                    ('name', '=', line.itemName),
                    ('company_id', 'in', [company_id, False])
                ], limit=1)
                if product:
                    _logger.info("   ✅ Found product by exact name: %s", product.name)

            # Third priority: Case-insensitive exact match
            if not product and line.itemName:
                product = self.env['product.product'].search([
                    ('name', '=ilike', line.itemName),
                    ('company_id', 'in', [company_id, False])
                ], limit=1)
                if product:
                    _logger.info("   ✅ Found product by case-insensitive name: %s", product.name)

            # Fourth priority: More controlled partial match
            if not product and line.itemName:
                product = self.env['product.product'].search([
                    ('name', 'ilike', f'%{line.itemName}%'),
                    ('company_id', 'in', [company_id, False])
                ], limit=1)
                if product:
                    _logger.info("   ✅ Found product by partial match: %s", product.name)

            if not product:
                _logger.warning(
                    "   ❌ No close product match found in company %s: %s (PLU: %s)",
                    company_id, line.itemName, line.pluCode
                )
                continue

            # Use tax from product configuration (from backup version)
            tax_ids = []

            # Get taxes from the product itself
            if product and product.taxes_id:
                # Filter taxes for the correct company
                product_taxes = product.taxes_id.filtered(lambda t: t.company_id.id == company_id)
                if product_taxes:
                    tax_ids = product_taxes.ids
                    tax_names = ', '.join(product_taxes.mapped('name'))
                    _logger.info("   ✅ Using product's configured taxes: %s for product %s",
                               tax_names, product.name)
                else:
                    # Try to use any tax configured on the product
                    if product.taxes_id:
                        tax_ids = product.taxes_id.ids
                        tax_names = ', '.join(product.taxes_id.mapped('name'))
                        _logger.info("   ✅ Using product's taxes (any company): %s for product %s",
                                   tax_names, product.name)

            # Log invoice vs product tax comparison
            tax_amount = line.lineTotalWithTax - line.lineTotal if line.lineTotalWithTax and line.lineTotal else 0
            _logger.info("   Tax comparison - Product: %s | Invoice Tax Rate: %s | Invoice Tax Amount: %.2f | Product Taxes: %s",
                        product.name, line.taxRate, tax_amount,
                        ', '.join(self.env['account.tax'].browse(tax_ids).mapped('name')) if tax_ids else "None")

            # Calculate correct price_unit (should be price without tax for tax-exclusive systems)
            if tax_amount > 0:
                # Price is tax-inclusive, extract base price
                price_unit_without_tax = line.lineTotal / line.quantity if line.quantity else line.price
            else:
                price_unit_without_tax = line.price

            _logger.info("   ✅ Product ready for order line: %s (ID: %s) | Price: %.2f | Taxes: %s",
                        product.name, product.id, price_unit_without_tax,
                        ', '.join(self.env['account.tax'].browse(tax_ids).mapped('name')) if tax_ids else "None")

            tax_id = False  # For backward compatibility
            if line.taxRate:
                _logger.info("   🔍 Looking up tax for rate: %.2f%%", line.taxRate)

                # STRATEGY 1: Exact match by amount (any type, any company)
                tax = self.env['account.tax'].search([
                    ('amount', '=', line.taxRate)
                ], limit=1)

                if tax:
                    tax_id = tax.id
                    _logger.info("      ✅ Found tax by exact rate: %s (Rate: %.2f%%, Company: %s, Type: %s)",
                               tax.name, tax.amount, tax.company_id.name if tax.company_id else 'All', tax.type_tax_use)
                else:
                    # STRATEGY 2: Close match (within 0.1% tolerance)
                    _logger.info("      ℹ️ Exact match failed, trying close match (±0.1%%)")
                    tax = self.env['account.tax'].search([
                        ('amount', '>=', line.taxRate - 0.1),
                        ('amount', '<=', line.taxRate + 0.1)
                    ], limit=1)

                    if tax:
                        tax_id = tax.id
                        _logger.info("      ✅ Found tax by close match: %s (Rate: %.2f%%, Company: %s, Type: %s)",
                                   tax.name, tax.amount, tax.company_id.name if tax.company_id else 'All', tax.type_tax_use)
                    else:
                        # STRATEGY 3: Search by name match (e.g., "15%" or "VAT 15")
                        _logger.info("      ℹ️ Close match failed, trying name match")
                        rate_str = str(int(line.taxRate)) if line.taxRate == int(line.taxRate) else str(line.taxRate)
                        tax = self.env['account.tax'].search([
                            ('name', 'ilike', f'{rate_str}%')
                        ], limit=1)

                        if tax:
                            tax_id = tax.id
                            _logger.info("      ✅ Found tax by name match: %s (Rate: %.2f%%, Company: %s, Type: %s)",
                                       tax.name, tax.amount, tax.company_id.name if tax.company_id else 'All', tax.type_tax_use)
                        else:
                            # STRATEGY 4: List ALL available taxes and find best match
                            _logger.warning("      ⚠️ No specific match for rate %.2f%%, checking ALL available taxes...", line.taxRate)

                            # Get all taxes in the company
                            company_taxes = self.env['account.tax'].search([
                                ('company_id', '=', company_id)
                            ])

                            # Also get taxes with no company restriction (generic)
                            generic_taxes = self.env['account.tax'].search([
                                ('company_id', '=', False)
                            ])

                            all_available = company_taxes | generic_taxes

                            if all_available:
                                _logger.warning("      📋 ALL taxes in company %s and generic:", company_id)
                                for t in all_available:
                                    _logger.warning("         - %s (Rate: %.2f%%, Type: %s, Company: %s)",
                                                  t.name, t.amount, t.type_tax_use,
                                                  t.company_id.name if t.company_id else 'Generic')

                                # Find best matching rate (within 1% tolerance)
                                best_tax = None
                                best_diff = float('inf')

                                for t in all_available:
                                    diff = abs(t.amount - line.taxRate)
                                    if diff < best_diff:
                                        best_diff = diff
                                        best_tax = t

                                if best_tax and best_diff < 1.0:  # Within 1% tolerance
                                    tax_id = best_tax.id
                                    _logger.info("      ✅ Using best matching tax: %s (Rate: %.2f%%, Invoice rate: %.2f%%, Diff: %.2f%%)",
                                               best_tax.name, best_tax.amount, line.taxRate, best_diff)
                                elif best_tax:
                                    # Even if not close, use it as last resort
                                    tax_id = best_tax.id
                                    _logger.warning("      ⚠️ Using best available tax (not close match): %s (Rate: %.2f%%, Invoice rate: %.2f%%)",
                                                  best_tax.name, best_tax.amount, line.taxRate)
                            else:
                                _logger.error("      ❌ NO TAXES FOUND IN ENTIRE SYSTEM! Check your tax configuration.")
                                _logger.error("      ℹ️ You need to create a tax for %.2f%% rate in Odoo", line.taxRate)
                                # Don't fail - just skip tax for this line
                                tax_id = False

            _logger.info("   ✅ Adding line: %s x %.2f @ %.2f = %.2f",
                        product.name, line.quantity, price_unit_without_tax, line.lineTotal)
            order_lines.append((0, 0, {
                'product_id': product.id,
                'full_product_name': product.name or line.itemName,
                'qty': line.quantity,
                'price_unit': price_unit_without_tax,  # Use price without tax
                'price_subtotal': line.lineTotal,
                'price_subtotal_incl': line.lineTotalWithTax,
                'tax_ids': [(6, 0, tax_ids)] if tax_ids else False,  # Use product's tax configuration
            }))

        if not order_lines:
            _logger.error("❌ No valid lines could be added for invoice FS %s", invoice.fsNumber)
            return False

        _logger.info("📝 [END] Order values prepared successfully:")
        _logger.info("   - FS Number: %s", invoice.fsNumber)
        _logger.info("   - Partner: %s (ID: %s)", self.env['res.partner'].browse(partner_id).name if partner_id else 'None', partner_id)
        _logger.info("   - Amount: %.2f (Tax: %.2f, Paid: %.2f)", invoice.totalWithTax, invoice.totalTax, invoice.totalPaid)
        _logger.info("   - Lines: %d items", len(order_lines))
        _logger.info("   - Session: %s", session.name)
        _logger.info("   - Employee: %s", self.env['hr.employee'].browse(employee_id).name if employee_id else 'None')

        # CRITICAL: Use SYNCED DATA directly from fiscal invoice - DON'T CALCULATE
        # The fiscal printer is the source of truth, not calculations

        # Amount that should be paid for the invoice (from fiscal data)
        amount_total = round(invoice.totalWithTax or 0.0, 2)

        # Amount paid for the invoice is ALWAYS the total (customer pays invoice amount)
        # The change is separate - it's money returned to customer
        amount_paid = amount_total  # MUST equal total, change is handled separately

        # Change/Rest given back to customer (from fiscal data)
        change_amount = round(invoice.change or 0.0, 2)

        # Tax amount (from fiscal data)
        tax_amount = round(invoice.totalTax or 0.0, 2)

        _logger.info("📝 Order amounts (from fiscal data): Total=%.2f, Tax=%.2f, Paid=%.2f, Change=%.2f",
                    amount_total, tax_amount, amount_paid, change_amount)

        return {
            'name': session.config_id.name,
            'fs_no': str(invoice.fsNumber).zfill(8),
            'fiscal_mrc': fiscal_mrc,
            'ej_checksum': invoice.checksum or '',
            'pos_reference': invoice.referenceNumber or '',
            'amount_total': amount_total,
            'amount_tax': tax_amount,
            'amount_paid': amount_paid,
            'amount_return': change_amount,
            'date_order': order_datetime,
            'partner_id': partner_id,
            'table_id': table_id,
            'session_id': session_id,
            'company_id': company_id,
            'employee_id': employee_id,
            'lines': order_lines,
            'payment_ids': [(0, 0, {
                'payment_method_id': payment_method_id,
                'amount': amount_paid,  # Use amount from fiscal invoice (totalWithTax)
                'payment_date': order_datetime,
            })] if payment_method_id else [],
        }

    @api.model
    def check_duplicate_fs(self, mrc, date):
        """Utility method to check for duplicate FS numbers."""
        if isinstance(date, str):
            date = datetime.strptime(date, "%Y-%m-%d").date()
        
        groups = self.read_group(
            domain=[
                ('fs_no', '!=', False),
                ('fiscal_mrc', '=', mrc),
                ('date_order', '>=', date),
                ('date_order', '<=', date),
                ('state', 'in', ['paid', 'done'])
            ],
            fields=['fs_no'],
            groupby=['fs_no'],
            lazy=False
        )
        
        duplicates = [(g['fs_no'], g['__count']) for g in groups if g['__count'] > 1]
        
        if duplicates:
            _logger.info("Found %d duplicate FS numbers for MRC %s on %s", len(duplicates), mrc, date)
            for fs_no, count in duplicates:
                _logger.info("  FS %s: %d occurrences", fs_no, count)
        else:
            _logger.info("No duplicate FS numbers found for MRC %s on %s", mrc, date)
        
        return duplicates
    
    @api.model
    def queue_daily_reconciliation_all_companies(self):
        """Public wrapper for daily reconciliation - can be called via XML-RPC"""
        return self._queue_daily_reconciliation_all_companies()
    
    @api.model
    def _queue_daily_reconciliation_all_companies(self):
        """Queue reconciliation jobs for all companies using existing logic"""
        companies = self.env['res.company'].search([])
        job_uuids = []

        for company in companies:
            devices = self.env['pos.device'].search([
                ('company_id', '=', company.id),
            ])

            for device in devices:
                if 'queue.job' in self.env:
                    # Queue a job for each device with staggered execution
                    delay_minutes = len(job_uuids) * 2  # 2 minutes between each job

                    # Use existing run_reconciliation_check with full integration context
                    job = self.with_company(company).with_context(
                        auto_invoice_created=True,
                        create_inventory_picking=True,
                        update_inventory_on_sync=True,
                        update_accounting_on_sync=False,  # Safer to not auto-update posted invoices
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
                else:
                    # Direct execution if queue_job not available
                    try:
                        self.with_company(company).with_context(
                            auto_invoice_created=True,
                            create_inventory_picking=True,
                            update_inventory_on_sync=True,
                            update_accounting_on_sync=False,
                        ).run_reconciliation_check(
                            target_mrc=device.mrc,
                            start_date=fields.Date.today(),
                            end_date=fields.Date.today()
                        )
                        _logger.info(f"Completed reconciliation for {company.name} - {device.name}")
                    except Exception as e:
                        _logger.error(f"Failed reconciliation for {company.name} - {device.name}: {str(e)}")
        
        # Send summary email
        if 'queue.job' in self.env:
            # Queue a summary job to run after all reconciliations
            summary_delay = len(job_uuids) * 2 + 10  # After all jobs + 10 minutes
            self.with_delay(
                priority=25,
                eta=fields.Datetime.now() + timedelta(minutes=summary_delay),
                description='Daily Reconciliation Summary'
            )._send_daily_reconciliation_summary(fields.Date.today())
        else:
            self._send_daily_reconciliation_summary(fields.Date.today())
        
        return job_uuids if job_uuids else True
    
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
            # Get admin users
            admin_users = self.env['res.users'].search([
                ('groups_id', 'in', self.env.ref('base.group_system').id)
            ])
            
            if admin_users:
                email_to = ','.join(admin_users.mapped('email'))
                
                mail_values = {
                    'subject': f'Daily POS Reconciliation Report - {fields.Date.today()}',
                    'body_html': content,
                    'email_to': email_to,
                    'email_from': self.env.company.email or 'noreply@company.com',
                }
                self.env['mail.mail'].create(mail_values).send()
                _logger.info("Reconciliation summary email sent to administrators")
        except Exception as e:
            _logger.error("Failed to send reconciliation email: %s", str(e))


class PosDailyReport(models.Model):
    _name = 'pos.daily.report'
    _description = 'POS Daily Report'
    _order = 'date desc, fiscal_mrc'

    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    fiscal_mrc = fields.Char(string='Fiscal MRC', required=True, index=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    
    # Counts
    pos_order_count = fields.Integer(string='POS Order Count')
    invoice_count = fields.Integer(string='Invoice Count')
    refund_count = fields.Integer(string='Refund Count')
    unmatched_fs_count = fields.Integer(string='Unmatched FS Count')
    
    # Totals
    session_total = fields.Float(string='Session Total', digits=(16, 2))
    z_report_total = fields.Float(string='Z Report Total', digits=(16, 2))
    refund_total = fields.Float(string='Refund Total', digits=(16, 2))
    net_order_total = fields.Float(string='Net Order Total', digits=(16, 2))
    net_invoice_total = fields.Float(string='Net Invoice Total', digits=(16, 2))
    zreport_sales_total = fields.Float(string='Z-Report Sales Total', digits=(16, 2))
    zreport_refund_total = fields.Float(string='Z-Report Refund Total', digits=(16, 2))
    net_zreport_total = fields.Float(string='Net Z-Report Total', digits=(16, 2))
    total_mismatch = fields.Float(string='Total Mismatch', digits=(16, 2))
    
    # Change counts
    recreated_orders = fields.Integer(string='Recreated Orders')
    updated_orders = fields.Integer(string='Updated Orders')
    cancelled_orders = fields.Integer(string='Cancelled Orders', compute='_compute_cancelled_orders')
    
    # Relations
    change_log_ids = fields.One2many('pos.change.log', 'daily_report_id', string='Change Logs')
    
    # Status
    reconciliation_status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], string='Status', default='pending')
    
    @api.depends('change_log_ids')
    def _compute_cancelled_orders(self):
        for report in self:
            report.cancelled_orders = len(report.change_log_ids.filtered(lambda l: l.change_type == 'cancelled'))


class PosZReportException(models.Model):
    _name = 'pos.zreport.exception'
    _description = 'POS Z-Report Exception Configuration'
    _order = 'date desc'

    date = fields.Date(string='Date', required=True, index=True)
    fiscal_mrc = fields.Char(string='Fiscal MRC', required=True, index=True)
    zreport_id = fields.Integer(string='Z-Report ID to Exclude')
    reason = fields.Text(string='Reason for Exclusion')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(string='Active', default=True)

    @api.model
    def get_excluded_zreport_ids(self, fiscal_mrc, start_date, end_date):
        """Get list of Z-report IDs to exclude for the given date range and MRC."""
        exceptions = self.search([
            ('fiscal_mrc', '=', fiscal_mrc),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('active', '=', True),
            ('company_id', '=', self.env.company.id)
        ])
        return [exc.zreport_id for exc in exceptions if exc.zreport_id]


class PosChangeLog(models.Model):
    _name = 'pos.change.log'
    _description = 'POS Change Log'
    _order = 'date desc'

    date = fields.Datetime(string='Change Date', default=fields.Datetime.now, index=True)
    pos_order_id = fields.Many2one('pos.order', string='POS Order', index=True)
    fs_no = fields.Char(string='FS Number', index=True)
    fiscal_mrc = fields.Char(string='Fiscal MRC', index=True)
    change_type = fields.Selection([
        ('recreated', 'Order Recreated'),
        ('amount_updated', 'Amount Updated'),
        ('cancelled', 'Order Cancelled'),
        ('linked', 'Order Linked'),
        ('updated_from_invoice', 'Updated from Invoice'),
        ('complete_update', 'Complete Update'),
        ('auto_invoiced', 'Auto Invoiced'),
        ('inventory_picking_created', 'Inventory Picking Created'),
        ('accounting_review_needed', 'Accounting Review Needed'),
    ], string='Change Type', required=True)
    old_value = fields.Char(string='Old Value')
    new_value = fields.Char(string='New Value')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    daily_report_id = fields.Many2one('pos.daily.report', string='Daily Report', index=True)

    @api.model
    def log_change(self, pos_order_id, fs_no, fiscal_mrc, change_type, old_value=None, new_value=None, daily_report_id=False):
        """Log a change made during reconciliation."""
        _logger.info("📝 Logging change: Order %s, FS %s, Type: %s", pos_order_id, fs_no, change_type)
        return self.create({
            'pos_order_id': pos_order_id,
            'fs_no': fs_no,
            'fiscal_mrc': fiscal_mrc,
            'change_type': change_type,
            'old_value': old_value,
            'new_value': new_value,
            'company_id': self.env.company.id,
            'daily_report_id': daily_report_id,
        })
