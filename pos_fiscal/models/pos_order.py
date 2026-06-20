from odoo import models, api, fields
from odoo.tools import float_is_zero
import logging

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    def _prepare_invoice_vals(self):
        """Override to ensure tax amounts are properly included."""
        # Check if parent method exists
        if hasattr(super(PosOrder, self), '_prepare_invoice_vals'):
            vals = super(PosOrder, self)._prepare_invoice_vals()
        else:
            # Create invoice values manually if parent method doesn't exist
            vals = {
                'move_type': 'out_invoice',
                'partner_id': self.partner_id.id,
                'invoice_date': fields.Date.context_today(self),
                'invoice_origin': self.name,
                'invoice_payment_term_id': False,
                'invoice_line_ids': [],
            }
        
        # Ensure the invoice type is set correctly
        vals['move_type'] = 'out_invoice'
        
        # Prepare invoice lines with taxes
        invoice_lines = []
        for line in self.lines.filtered(lambda l: l.product_id):
            line_vals = self._prepare_invoice_line(line)
            invoice_lines.append((0, 0, line_vals))
            
        if invoice_lines:
            vals['invoice_line_ids'] = invoice_lines
        
        _logger.info("Preparing invoice vals for POS order %s with %d lines", 
                    self.name, len(invoice_lines))
        
        return vals
    
    def _prepare_invoice_line(self, order_line):
        """Override to ensure taxes are included in invoice lines."""
        # First check if the parent method exists
        if hasattr(super(PosOrder, self), '_prepare_invoice_line'):
            res = super(PosOrder, self)._prepare_invoice_line(order_line)
        else:
            # Create invoice line data manually if parent method doesn't exist
            res = {
                'product_id': order_line.product_id.id,
                'name': order_line.full_product_name or order_line.product_id.name,
                'quantity': order_line.qty,
                'price_unit': order_line.price_unit,
                'product_uom_id': order_line.product_id.uom_id.id,
                'discount': order_line.discount if hasattr(order_line, 'discount') else 0.0,
            }
        
        # Ensure taxes are included
        if order_line.tax_ids:
            res['tax_ids'] = [(6, 0, order_line.tax_ids.ids)]
            _logger.info("Prepared invoice line with taxes %s for product %s", 
                        order_line.tax_ids.mapped('name'), order_line.product_id.name)
        
        # Ensure correct price calculation (price should be without tax)
        res['price_unit'] = order_line.price_unit
        # Ensure discount is included (important for accurate invoice totals)
        if hasattr(order_line, 'discount'):
            res['discount'] = order_line.discount
            _logger.info("Set price unit to %.2f with discount %.2f%% for product %s",
                        res['price_unit'], res['discount'], order_line.product_id.name)
        else:
            _logger.info("Set price unit to %.2f for product %s", res['price_unit'], order_line.product_id.name)

        return res
    
    def action_pos_order_invoice(self):
        """Override to ensure taxes are properly applied to the invoice."""
        self.ensure_one()
        
        # Log the order details before invoicing
        _logger.info("=" * 60)
        _logger.info("STARTING INVOICE CREATION - pos_fiscal override")
        _logger.info("POS Order: %s | FS: %s | State: %s", self.name, self.fs_no, self.state)
        _logger.info("Order total: %.2f, Tax total: %.2f", self.amount_total, self.amount_tax)
        _logger.info("=" * 60)
        
        # Log tax information from order lines
        for line in self.lines:
            if line.tax_ids:
                tax_names = ', '.join(line.tax_ids.mapped('name'))
                _logger.info("Order Line: %s | Qty: %.2f | Price: %.2f | Taxes: %s | Tax Amount: %.2f", 
                           line.product_id.name, line.qty, line.price_unit, tax_names, 
                           line.price_subtotal_incl - line.price_subtotal)
        
        # If there is already an invoice, remove it first
        if self.account_move:
            _logger.info("🗑️ Removing existing invoice %s before creating new one", self.account_move.name)
            try:
                # Cancel the invoice if it's posted
                if self.account_move.state == 'posted':
                    self.account_move.button_draft()
                # Delete the invoice
                old_invoice_id = self.account_move.id
                self.account_move.unlink()
                _logger.info("✅ Removed existing invoice ID: %s", old_invoice_id)
                # Clear the account_move reference
                self.write({'account_move': False})
            except Exception as e:
                _logger.error("❌ Error removing existing invoice: %s", str(e))
                # Continue anyway as we'll try to create a new invoice
        
        try:
            # If the standard method doesn't exist, create invoice manually
            if not hasattr(super(PosOrder, self), 'action_pos_order_invoice'):
                _logger.info("Creating invoice manually for POS order %s", self.name)
                
                # Prepare invoice values with tax lines
                invoice_vals = self._prepare_invoice_vals()
                
                # Create the invoice
                invoice = self.env['account.move'].create(invoice_vals)
                
                # Link the invoice to the order
                self.write({'account_move': invoice.id, 'state': 'invoiced'})
                
                # Post the invoice if needed
                if invoice.state == 'draft':
                    invoice.action_post()
                
                _logger.info("✅ Manual invoice created: %s", invoice.name)
                result = invoice
            else:
                # Call super to create the invoice
                result = super(PosOrder, self).action_pos_order_invoice()
            
            # Get the created invoice
            if self.account_move:
                invoice = self.account_move
                _logger.info("Invoice created: %s (State: %s)", invoice.name, invoice.state)
                
                # Double-check and ensure taxes are applied from order lines to invoice lines
                for pos_line in self.lines.filtered(lambda l: l.product_id):
                    # Find corresponding invoice line
                    invoice_lines = invoice.invoice_line_ids.filtered(
                        lambda l: l.product_id == pos_line.product_id
                    )
                    
                    for invoice_line in invoice_lines:
                        if pos_line.tax_ids and not invoice_line.tax_ids:
                            # Apply taxes from POS line to invoice line if missing
                            invoice_line.with_context(check_move_validity=False).write({
                                'tax_ids': [(6, 0, pos_line.tax_ids.ids)],
                                'price_unit': pos_line.price_unit,  # Ensure price is without tax
                            })
                            _logger.info("✅ Applied taxes %s to invoice line for product %s (price: %.2f)", 
                                       pos_line.tax_ids.mapped('name'), pos_line.product_id.name, pos_line.price_unit)
                
                # Recompute all taxes and totals
                invoice.with_context(check_move_validity=False)._recompute_dynamic_lines()
                
                _logger.info("Tax recomputation completed for invoice %s", invoice.name)
                _logger.info("Final Invoice - Total: %.2f | Tax: %.2f | Untaxed: %.2f", 
                           invoice.amount_total, invoice.amount_tax, invoice.amount_untaxed)
            
            return result
            
        except Exception as e:
            _logger.error("❌ Error creating invoice for POS order %s: %s", self.name, str(e))
            # Log more details about the error
            import traceback
            _logger.error("Traceback: %s", traceback.format_exc())
            raise
    
    def _create_order_picking(self):
        """Create stock picking using pos_etta's method when available"""
        self.ensure_one()
        
        _logger.info("=" * 60)
        _logger.info("🚀 INVENTORY CREATION START - Order %s (FS: %s)", self.id, self.fs_no)
        _logger.info("=" * 60)
        
        # Essential checks
        if not self.session_id:
            _logger.error("❌ No session for order %s", self.name)
            return False
        
        if not self.lines:
            _logger.warning("❌ No lines in order %s", self.name)
            return False
        
        # Get config from session (pos_etta needs this)
        config = self.session_id.config_id
        if not config:
            _logger.error("❌ No config in session %s", self.session_id.name)
            return False
        
        # IMPORTANT: pos_etta uses stock_location_id from config
        if not config.stock_location_id:
            _logger.error("❌ No stock_location_id in config %s", config.name)
            # Try to set it
            default_location = self.env['stock.warehouse'].search([
                ('company_id', '=', self.company_id.id)
            ], limit=1).lot_stock_id
            if default_location:
                config.stock_location_id = default_location
                _logger.info("✅ Set stock_location_id to %s", default_location.name)
            else:
                return False
        
        # Get picking type
        picking_type = config.picking_type_id
        if not picking_type:
            _logger.error("❌ No picking_type in config %s", config.name)
            # Try to find one
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            if picking_type:
                config.picking_type_id = picking_type
                _logger.info("✅ Set picking_type to %s", picking_type.name)
            else:
                return False
        
        # Set location_id on order (pos_etta expects this)
        if not self.location_id:
            self.location_id = config.stock_location_id
        
        # Get destination location
        if self.partner_id and self.partner_id.property_stock_customer:
            location_dest_id = self.partner_id.property_stock_customer.id
        else:
            location_dest_id = picking_type.default_location_dest_id.id
        
        if not location_dest_id:
            _logger.warning("No destination location found for POS order %s", self.name)
            return False
        
        # Log what we're working with
        _logger.info("📋 Order Details:")
        _logger.info("  - Config: %s (ID: %s)", config.name, config.id)
        _logger.info("  - Picking Type: %s (ID: %s)", picking_type.name, picking_type.id)
        _logger.info("  - Stock Location: %s (ID: %s)", config.stock_location_id.name, config.stock_location_id.id)
        _logger.info("  - Order Location: %s", self.location_id.name if self.location_id else "NOT SET")
        _logger.info("  - Partner: %s", self.partner_id.name if self.partner_id else "Walk-in Customer")
        
        # Check product types
        _logger.info("📦 Checking %d products:", len(self.lines))
        stockable_lines = []
        for line in self.lines:
            product = line.product_id
            product_type = product.detailed_type if hasattr(product, 'detailed_type') else product.type
            is_stockable = product_type in ['product', 'consu']
            _logger.info("  - %s: type=%s, qty=%.2f, stockable=%s", 
                        product.name, product_type, line.qty, is_stockable)
            if is_stockable and line.qty != 0:
                stockable_lines.append(line)
        
        if not stockable_lines:
            _logger.warning("⚠️ No stockable products found")
            return False
        
        _logger.info("✅ Found %d stockable lines", len(stockable_lines))
        
        # Check if pos_etta method exists
        if hasattr(self.env['stock.picking'], '_create_picking_from_pos_order_lines'):
            _logger.info("🔧 Using pos_etta's _create_picking_from_pos_order_lines")
            _logger.info("  - Destination Location ID: %s", location_dest_id)
            
            # Call pos_etta's method
            try:
                # Convert to recordset if needed
                lines_recordset = self.env['pos.order.line'].browse([l.id for l in stockable_lines])
                
                pickings = self.env['stock.picking']._create_picking_from_pos_order_lines(
                    location_dest_id=location_dest_id,
                    lines=lines_recordset,
                    picking_type=picking_type,
                    partner=self.partner_id
                )

                if pickings:
                    _logger.info("✅ pos_etta created %d picking(s)", len(pickings))

                    # AUTO-VALIDATE pickings to 'done' state
                    for picking in pickings:
                        _logger.info("  - Picking: %s (State: %s)", picking.name, picking.state)

                        try:
                            # Set quantities done for all moves
                            for move in picking.move_ids_without_package:
                                if move.product_uom_qty > 0:
                                    move.quantity_done = move.product_uom_qty
                                    _logger.info("    ✓ Set qty_done=%.2f for %s", move.quantity_done, move.product_id.name)

                            # Validate the picking based on its current state
                            if picking.state == 'draft':
                                picking.action_confirm()
                                _logger.info("    ✓ Picking confirmed")

                            if picking.state in ['confirmed', 'waiting']:
                                picking.action_assign()
                                _logger.info("    ✓ Picking assigned")

                            if picking.state == 'assigned':
                                picking.button_validate()
                                _logger.info("    ✅ Picking validated to state: %s", picking.state)

                        except Exception as e:
                            _logger.error("    ❌ Error auto-validating picking %s: %s", picking.name, str(e))
                else:
                    _logger.warning("⚠️ pos_etta returned no pickings")

                return pickings
                
            except Exception as e:
                _logger.error("❌ Error calling pos_etta method: %s", str(e))
                import traceback
                _logger.error("Traceback: %s", traceback.format_exc())
                return False
        else:
            _logger.error("❌ pos_etta method not found! Check if pos_etta is installed")
            
            # Fallback to basic creation
            _logger.info("🔧 Using fallback basic picking creation")
            pickings = self.env['stock.picking']
            
            # Separate positive and negative lines
            positive_lines = self.env['pos.order.line'].browse([l.id for l in stockable_lines if l.qty > 0])
            negative_lines = self.env['pos.order.line'].browse([l.id for l in stockable_lines if l.qty < 0])
            
            # Create picking for positive lines
            if positive_lines:
                _logger.info("Creating outgoing picking for %d positive lines", len(positive_lines))
            else:
                # Fallback to standard creation
                picking_vals = {
                    'partner_id': self.partner_id.id if self.partner_id else False,
                    'picking_type_id': picking_type.id,
                    'location_id': self.location_id.id if hasattr(self, 'location_id') else picking_type.default_location_src_id.id,
                    'location_dest_id': location_dest_id,
                    'origin': self.name,
                    'state': 'draft',
                }
                
                positive_picking = self.env['stock.picking'].create(picking_vals)
                _logger.info("✅ INVENTORY CREATED - Picking: %s | Type: %s | State: %s",
                            positive_picking.name, positive_picking.picking_type_id.name, positive_picking.state)
                
                # Create stock moves for each line
                for line in positive_lines:
                    move_vals = {
                        'name': line.product_id.name,
                        'product_id': line.product_id.id,
                        'product_uom_qty': abs(line.qty),
                        'product_uom': line.product_id.uom_id.id,
                        'picking_id': positive_picking.id,
                        'location_id': positive_picking.location_id.id,
                        'location_dest_id': positive_picking.location_dest_id.id,
                        'company_id': self.company_id.id,
                        'state': 'draft',
                    }
                    self.env['stock.move'].create(move_vals)
                
                # Confirm and assign the picking
                try:
                    positive_picking.action_confirm()
                    positive_picking.action_assign()
                    
                    # If all quantities are available, validate the picking
                    if positive_picking.state == 'assigned':
                        for move in positive_picking.move_ids:
                            move.quantity = move.product_uom_qty
                        positive_picking.button_validate()
                        _logger.info("Picking %s validated successfully", positive_picking.name)
                    else:
                        _logger.warning("Picking %s not fully available", positive_picking.name)
                        
                except Exception as e:
                    _logger.error("❌ INVENTORY CREATION FAILED for POS Order %s: %s", 
                                 self.name, str(e))
                    _logger.error("Error processing picking %s: %s", positive_picking.name, str(e))
                
                pickings |= positive_picking
        
        # Create picking for negative lines (returns)
        if negative_lines:
            _logger.info("Creating return picking for %d negative lines", len(negative_lines))
            
            # Get return picking type
            return_picking_type = picking_type.return_picking_type_id or picking_type
            
            # For returns, swap source and destination
            return_location_id = return_picking_type.default_location_dest_id.id or picking_type.default_location_src_id.id
            
            if hasattr(self.env['stock.picking'], '_create_picking_from_pos_order_lines'):
                # Use the enhanced method if available
                negative_picking = self.env['stock.picking']._create_picking_from_pos_order_lines(
                    return_location_id,
                    negative_lines,
                    return_picking_type,
                    self.partner_id
                )
                pickings |= negative_picking
            else:
                # Fallback to standard creation
                return_vals = {
                    'partner_id': self.partner_id.id if self.partner_id else False,
                    'picking_type_id': return_picking_type.id,
                    'location_id': location_dest_id,  # Customer location as source for returns
                    'location_dest_id': return_location_id,  # Stock location as destination
                    'origin': f"Return of {self.name}",
                    'state': 'draft',
                }
                
                negative_picking = self.env['stock.picking'].create(return_vals)
                _logger.info("✅ INVENTORY CREATED (RETURN) - Picking: %s | Type: %s | State: %s",
                            negative_picking.name, negative_picking.picking_type_id.name, negative_picking.state)
                
                # Create stock moves for return lines
                for line in negative_lines:
                    move_vals = {
                        'name': f"Return: {line.product_id.name}",
                        'product_id': line.product_id.id,
                        'product_uom_qty': abs(line.qty),
                        'product_uom': line.product_id.uom_id.id,
                        'picking_id': negative_picking.id,
                        'location_id': negative_picking.location_id.id,
                        'location_dest_id': negative_picking.location_dest_id.id,
                        'company_id': self.company_id.id,
                        'state': 'draft',
                    }
                    self.env['stock.move'].create(move_vals)
                
                # Process return picking
                try:
                    negative_picking.action_confirm()
                    negative_picking.action_assign()
                    
                    if negative_picking.state == 'assigned':
                        for move in negative_picking.move_ids:
                            move.quantity = move.product_uom_qty
                        negative_picking.button_validate()
                        _logger.info("Return picking %s validated successfully", negative_picking.name)
                    else:
                        _logger.warning("Return picking %s not fully available", negative_picking.name)
                        
                except Exception as e:
                    _logger.error("❌ INVENTORY RETURN CREATION FAILED for POS Order %s: %s", 
                                 self.name, str(e))
                    _logger.error("Error processing return picking %s: %s", negative_picking.name, str(e))
                
                pickings |= negative_picking
        
        if pickings:
            _logger.info("Successfully created %d picking(s) for POS order %s", len(pickings), self.name)
            _logger.info("=" * 60)
            _logger.info("INVENTORY MOVEMENT SUMMARY")
            _logger.info("Total Pickings Created: %d", len(pickings))
            for picking in pickings:
                _logger.info("- %s: %s (State: %s)", 
                            picking.picking_type_id.name, picking.name, picking.state)
            _logger.info("=" * 60)
        else:
            _logger.warning("No pickings created for POS order %s", self.name)
            _logger.info("=" * 60)
            _logger.info("INVENTORY MOVEMENT SUMMARY")
            _logger.info("No inventory movements created")
            _logger.info("=" * 60)
        
        return pickings

    def _regenerate_order_picking(self):
        """Regenerate stock picking for an existing order after update"""
        self.ensure_one()

        _logger.info("🔄 Regenerating picking for updated order %s", self.id)

        # IMPROVED: Search for pickings using multiple criteria
        # Some pickings use pos_order_id, others use origin field
        search_domain = [
            '|', '|',
            ('pos_order_id', '=', self.id),
            ('origin', '=', self.name),
            ('origin', '=', self.pos_reference)
        ]

        existing_pickings = self.env['stock.picking'].search(search_domain)

        if existing_pickings:
            _logger.info("🔍 Found %d existing picking(s) for order %s", len(existing_pickings), self.name)

        # Cancel/delete ALL existing pickings (including waiting state)
        for picking in existing_pickings:
            try:
                if picking.state == 'draft':
                    _logger.info("🗑️ Deleting draft picking %s", picking.name)
                    picking.unlink()
                elif picking.state in ['waiting', 'confirmed', 'assigned']:
                    # Cancel and delete the picking - FORCE CANCEL
                    _logger.info("❌ Force cancelling picking %s (state: %s)", picking.name, picking.state)
                    # First try to cancel
                    try:
                        picking.action_cancel()
                    except:
                        # If cancel fails, force state change
                        _logger.warning("⚠️ Normal cancel failed, forcing state to cancel")
                        picking.write({'state': 'cancel'})
                    # Then delete
                    picking.unlink()
                    _logger.info("✅ Successfully removed picking %s", picking.name)
                elif picking.state == 'done':
                    # For done pickings, log warning but don't interfere
                    _logger.warning("⚠️ Skipping completed picking %s (state: done)", picking.name)
            except Exception as e:
                _logger.error("❌ Error handling existing picking %s: %s", picking.name, str(e))

        # Now create a new picking with the updated order data
        new_picking = self._create_order_picking()

        # Ensure the new picking is properly linked to the order
        if new_picking:
            for picking in new_picking:
                # Set proper linking
                picking.write({
                    'pos_order_id': self.id,
                    'origin': self.name or self.pos_reference,
                    'partner_id': self.partner_id.id if self.partner_id else False
                })

                # AUTO-VALIDATE: Move picking to 'done' state
                try:
                    _logger.info("🔄 Auto-validating picking %s", picking.name)

                    # Check if picking has moves
                    if not picking.move_ids_without_package:
                        _logger.warning("⚠️ Picking %s has no moves, skipping validation", picking.name)
                        continue

                    # Set quantities done for all moves
                    for move in picking.move_ids_without_package:
                        if move.product_uom_qty > 0:
                            move.quantity_done = move.product_uom_qty
                            _logger.info("  ✓ Set qty_done=%.2f for %s", move.quantity_done, move.product_id.name)

                    # Validate the picking (this processes the inventory movement)
                    if picking.state in ['draft', 'waiting', 'confirmed', 'assigned']:
                        # Force assign first if needed
                        if picking.state in ['draft', 'waiting', 'confirmed']:
                            picking.action_assign()

                        # Then validate
                        picking.button_validate()
                        _logger.info("✅ Picking %s validated to state: %s", picking.name, picking.state)
                    else:
                        _logger.warning("⚠️ Picking %s already in state: %s", picking.name, picking.state)

                except Exception as e:
                    _logger.error("❌ Error auto-validating picking %s: %s", picking.name, str(e))
                    _logger.warning("   Picking created but not validated - manual validation may be required")

            _logger.info("✅ Successfully regenerated and validated %d picking(s) for order %s", len(new_picking), self.id)
        else:
            _logger.warning("⚠️ Could not regenerate picking for order %s", self.id)

        return new_picking

    def _ensure_pos_config_for_inventory(self):
        """Ensure POS config has required fields for inventory"""
        self.ensure_one()
        
        if not self.session_id or not self.session_id.config_id:
            return False
        
        config = self.session_id.config_id
        needs_update = False
        
        # Check stock_location_id (required by pos_etta)
        if not config.stock_location_id:
            warehouse = self.env['stock.warehouse'].search([
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            if warehouse:
                config.stock_location_id = warehouse.lot_stock_id
                needs_update = True
                _logger.info("✅ Set stock_location_id for config %s", config.name)
        
        # Check picking_type_id
        if not config.picking_type_id:
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing'),
                ('company_id', '=', self.company_id.id),
                ('warehouse_id', '!=', False)
            ], limit=1)
            if picking_type:
                config.picking_type_id = picking_type
                needs_update = True
                _logger.info("✅ Set picking_type_id for config %s", config.name)
        
        return True
    
    def write(self, vals):
        """Override write to handle picking regeneration when order lines change"""
        # Store which orders need picking regeneration
        orders_needing_regeneration = self.env['pos.order']

        # Check if this is an update that affects inventory
        if 'lines' in vals:
            # These orders will need their pickings regenerated
            orders_needing_regeneration = self.filtered(lambda o: o.id)
            _logger.info("🔄 Detected order line changes for %d order(s)", len(orders_needing_regeneration))

        # Call parent write
        res = super(PosOrder, self).write(vals)

        # Regenerate pickings for affected orders
        for order in orders_needing_regeneration:
            try:
                _logger.info("🔄 Regenerating picking for updated order %s", order.name)
                order._regenerate_order_picking()
            except Exception as e:
                _logger.error("❌ Error regenerating picking for order %s: %s", order.name, str(e))

        return res

    @api.model
    def reconcile_pos_orders_with_zreports(self, date, device_id):
        # Fetch Z Reports for the device and date
        z_reports = self.env['pos.zreport'].search([
            ('device_id', '=', device_id),
            ('date', '=', date),
        ])
        zreport_total = sum(z.salesTotal for z in z_reports)

        # Fetch POS Orders for the device (fiscal_mrc) and date
        pos_orders = self.env['pos.order'].search([
            ('fiscal_mrc', '=', z_reports[0].device_id.mrc if z_reports else False),
            ('date_order', '=', date),
        ])
        pos_order_total = sum(o.amount_total for o in pos_orders if o.state in ['paid', 'done', 'invoiced'])