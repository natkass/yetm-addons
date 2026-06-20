# Implementation Plan: Kestedemena POS Behavior Fix

## Overview
This document provides the specific code changes needed to implement Kestedemena's business requirements in the POS system.

## Phase 1: Configuration Setup

### 1.1 Add Configuration Fields to POS Config
**File**: `pos_etta/models/pos_config.py`

Add these fields after line 214:

```python
# Kestedemena Business Mode Configuration
kestedemena_mode = fields.Boolean(
    "Kestedemena Business Mode", 
    default=False,
    help="Enable Kestedemena-specific business flow: receipts printed at payment, manufacturing after payment, delivery after manufacturing"
)

delivery_order_state = fields.Selection([
    ('ready', 'Ready for Manual Validation'),
    ('done', 'Done (Immediate)')
], 
    string='Delivery Order State', 
    default='ready',
    help="State of delivery orders created from POS orders"
)

prevent_stock_deduction = fields.Boolean(
    "Prevent Immediate Stock Deduction", 
    default=True,
    help="Prevent stock deduction until manual validation by storekeeper"
)

require_manual_validation = fields.Boolean(
    "Require Manual Delivery Validation", 
    default=True,
    help="Require storekeeper to manually validate delivery before stock deduction"
)
```

### 1.2 Add Configuration to Settings
**File**: `pos_etta/models/res_config_settings.py`

Add these fields to the ResConfigSettings class:

```python
# Kestedemena Configuration
kestedemena_mode = fields.Boolean(
    related="pos_config_id.kestedemena_mode", 
    readonly=False,
    string="Kestedemena Business Mode"
)

delivery_order_state = fields.Selection(
    related="pos_config_id.delivery_order_state", 
    readonly=False,
    string="Delivery Order State"
)

prevent_stock_deduction = fields.Boolean(
    related="pos_config_id.prevent_stock_deduction", 
    readonly=False,
    string="Prevent Immediate Stock Deduction"
)

require_manual_validation = fields.Boolean(
    related="pos_config_id.require_manual_validation", 
    readonly=False,
    string="Require Manual Delivery Validation"
)
```

## Phase 2: Stock Movement Logic Modification

### 2.1 Modify Stock Picking Creation
**File**: `pos_etta/models/bi_pos_stock.py`

Replace the `_create_picking_from_pos_order_lines` method (lines 228-281):

```python
@api.model
def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
    """We'll create some picking based on order_lines"""

    pickings = self.env['stock.picking']
    stockable_lines = lines.filtered(
        lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty,
                                                                                  precision_rounding=l.product_id.uom_id.rounding))
    if not stockable_lines:
        return pickings
    positive_lines = stockable_lines.filtered(lambda l: l.qty > 0)
    negative_lines = stockable_lines - positive_lines

    if positive_lines:
        pos_order = positive_lines[0].order_id
        location_id = pos_order.location_id.id
        vals = self._prepare_picking_vals(partner, picking_type, location_id, location_dest_id)
        positive_picking = self.env['stock.picking'].create(vals)
        positive_picking._create_move_from_pos_order_lines(positive_lines)
        
        # Kestedemena Business Mode Logic
        if pos_order.config_id.kestedemena_mode:
            try:
                with self.env.cr.savepoint():
                    # Create delivery order in Ready state for manual validation
                    positive_picking.action_confirm()
                    positive_picking.write({'state': 'ready'})
                    
                    # Don't deduct stock immediately - wait for manual validation
                    if pos_order.config_id.prevent_stock_deduction:
                        # Mark moves as not done to prevent stock deduction
                        for move in positive_picking.move_lines:
                            move.write({'state': 'confirmed'})
                            
            except (UserError, ValidationError):
                pass
        else:
            # Standard behavior
            try:
                with self.env.cr.savepoint():
                    positive_picking.action_confirm()
                    positive_picking.write({'state': 'waiting'})
            except (UserError, ValidationError):
                pass
        
        pickings |= positive_picking
        
    if negative_lines:
        if picking_type.return_picking_type_id:
            return_picking_type = picking_type.return_picking_type_id
            return_location_id = return_picking_type.default_location_dest_id.id
        else:
            return_picking_type = picking_type
            return_location_id = picking_type.default_location_src_id.id

        vals = self._prepare_picking_vals(partner, return_picking_type, location_dest_id, return_location_id)
        negative_picking = self.env['stock.picking'].create(vals)
        negative_picking._create_move_from_pos_order_lines(negative_lines)
        
        # Kestedemena Business Mode Logic for Returns
        if negative_lines[0].order_id.config_id.kestedemena_mode:
            try:
                with self.env.cr.savepoint():
                    negative_picking.action_confirm()
                    negative_picking.write({'state': 'ready'})
            except (UserError, ValidationError):
                pass
        else:
            try:
                with self.env.cr.savepoint():
                    negative_picking.action_confirm()
                    negative_picking.write({'state': 'waiting'})
            except (UserError, ValidationError):
                pass

        pickings |= negative_picking
    return pickings
```

## Phase 3: Sales Order Processing Override

### 3.1 Modify Order Processing
**File**: `pos_etta/models/pos_orderline.py`

Replace the `_process_order` method (lines 120-150):

```python
@api.model
def _process_order(self, order, draft, existing_order):
    # Check if Kestedemena mode is enabled
    pos_config = self.env['pos.config'].browse(order.get('config_id'))
    
    if pos_config.kestedemena_mode:
        # Kestedemena Business Mode: Don't cancel sales orders
        result = super(PosOrderInherit, self)._process_order(order, draft, existing_order)
        pos_order = self.search([('id', '=', result)])
        
        # Handle sales order origin if exists
        if order.get('sale_order_origin_id'):
            sale_order = self.env['sale.order'].browse(order['sale_order_origin_id'])
            if sale_order.exists():
                # Keep sales order confirmed, don't cancel
                sale_order.write({'state': 'sale'})
                
                # Create delivery order in Ready state
                if pos_order.picking_ids:
                    for picking in pos_order.picking_ids:
                        picking.write({'state': 'ready'})
        
        # MRP Order Creation (existing logic)
        mrp_order = self.env['mrp.production']
        if pos_order.config_id.create_mrp_order and draft == False:
            for line in pos_order.lines:
                route_ids = line.product_id.route_ids.mapped('name')
                if 'Manufacture' in route_ids:
                    if line.product_id.bom_ids and line.qty > 0:
                        mrp_order = mrp_order.create({
                            'product_id': line.product_id.id,
                            'product_qty': line.qty,
                            'date_start': datetime.now(),
                            'user_id': self.env.user.id,
                            'company_id': self.env.company.id,
                            'origin': pos_order.pos_reference
                        })
                        mrp_order.action_confirm()
                        if pos_order.config_id.is_done:
                            mrp_order.write({
                                'qty_producing': line.qty,
                            })
                            for move_line in mrp_order.move_raw_ids:
                                move_line.write({'quantity': move_line.product_uom_qty, 'picked': True})
                            mrp_order.button_mark_done()
    else:
        # Standard behavior
        result = super(PosOrderInherit, self)._process_order(order, draft, existing_order)
        pos_order = self.search([('id', '=', result)])
        
        # Standard MRP order creation
        mrp_order = self.env['mrp.production']
        if pos_order.config_id.create_mrp_order and draft == False:
            for line in pos_order.lines:
                route_ids = line.product_id.route_ids.mapped('name')
                if 'Manufacture' in route_ids:
                    if line.product_id.bom_ids and line.qty > 0:
                        mrp_order = mrp_order.create({
                            'product_id': line.product_id.id,
                            'product_qty': line.qty,
                            'date_start': datetime.now(),
                            'user_id': self.env.user.id,
                            'company_id': self.env.company.id,
                            'origin': pos_order.pos_reference
                        })
                        mrp_order.action_confirm()
                        if pos_order.config_id.is_done:
                            mrp_order.write({
                                'qty_producing': line.qty,
                            })
                            for move_line in mrp_order.move_raw_ids:
                                move_line.write({'quantity': move_line.product_uom_qty, 'picked': True})
                            mrp_order.button_mark_done()
    
    return result
```

## Phase 4: Manual Validation Interface

### 4.1 Create Manual Validation Wizard
**File**: `pos_etta/wizard/delivery_validation.py`

```python
from odoo import fields, models, api, _
from odoo.exceptions import UserError

class DeliveryValidationWizard(models.TransientModel):
    _name = 'delivery.validation.wizard'
    _description = 'Delivery Validation Wizard'

    picking_id = fields.Many2one('stock.picking', string='Delivery Order', required=True)
    validated_by = fields.Many2one('res.users', string='Validated By', default=lambda self: self.env.user)
    validation_date = fields.Datetime(string='Validation Date', default=fields.Datetime.now)
    notes = fields.Text(string='Notes')

    def action_validate_delivery(self):
        """Validate delivery and deduct stock"""
        for wizard in self:
            if wizard.picking_id.state != 'ready':
                raise UserError(_('Only delivery orders in Ready state can be validated.'))
            
            # Mark delivery as done
            wizard.picking_id.action_confirm()
            wizard.picking_id.button_validate()
            
            # Update validation info
            wizard.picking_id.write({
                'validated_by': wizard.validated_by.id,
                'validation_date': wizard.validation_date,
                'validation_notes': wizard.notes,
            })
            
            # Create stock moves and deduct stock
            for move in wizard.picking_id.move_lines:
                move._action_done()
        
        return {'type': 'ir.actions.act_window_close'}
```

### 4.2 Add Validation Fields to Stock Picking
**File**: `pos_etta/models/bi_pos_stock.py`

Add these fields to the StockPicking class:

```python
# Add to StockPicking class
validated_by = fields.Many2one('res.users', string='Validated By')
validation_date = fields.Datetime(string='Validation Date')
validation_notes = fields.Text(string='Validation Notes')
is_kestedemena_delivery = fields.Boolean(string='Kestedemena Delivery', compute='_compute_is_kestedemena_delivery')

@api.depends('pos_order_id.config_id.kestedemena_mode')
def _compute_is_kestedemena_delivery(self):
    for picking in self:
        picking.is_kestedemena_delivery = picking.pos_order_id.config_id.kestedemena_mode if picking.pos_order_id else False
```

## Phase 5: UI Updates

### 5.1 Add Configuration UI
**File**: `pos_etta/views/pos_config_views.xml`

Add this section to the POS configuration form:

```xml
<group string="Kestedemena Business Mode" attrs="{'invisible': [('kestedemena_mode', '=', False)]}">
    <field name="kestedemena_mode"/>
    <field name="delivery_order_state"/>
    <field name="prevent_stock_deduction"/>
    <field name="require_manual_validation"/>
</group>
```

### 5.2 Add Manual Validation Button
**File**: `pos_etta/views/stock_picking_views.xml`

Add this button to the stock picking form:

```xml
<button name="action_manual_validate" 
        string="Manual Validate" 
        type="object" 
        class="oe_highlight"
        attrs="{'invisible': [('state', '!=', 'ready'), ('is_kestedemena_delivery', '=', False)]}"/>
```

## Testing Checklist

### Configuration Testing
- [ ] Enable Kestedemena mode in POS configuration
- [ ] Verify delivery order state defaults to 'ready'
- [ ] Verify prevent stock deduction is enabled by default

### Sales Order → POS Testing
- [ ] Create and confirm sales order
- [ ] Process payment in POS
- [ ] Verify sales order remains confirmed (not cancelled)
- [ ] Verify delivery order created in 'ready' state
- [ ] Verify no immediate stock deduction

### Direct POS Sale Testing
- [ ] Sell product directly through POS
- [ ] Verify delivery order created in 'ready' state
- [ ] Verify no immediate stock deduction
- [ ] Verify manual validation button appears

### Manual Validation Testing
- [ ] Open delivery order in 'ready' state
- [ ] Click manual validate button
- [ ] Verify delivery order moves to 'done' state
- [ ] Verify stock is deducted after validation
- [ ] Verify validation info is recorded

### Standard Mode Testing
- [ ] Disable Kestedemena mode
- [ ] Verify standard POS behavior is maintained
- [ ] Verify immediate stock deduction works
- [ ] Verify sales order cancellation works

## Deployment Steps

1. **Backup**: Create backup of current system
2. **Code Changes**: Apply all code modifications
3. **Database Update**: Update modules and restart services
4. **Configuration**: Enable Kestedemena mode in POS configurations
5. **Testing**: Run through all test scenarios
6. **Training**: Train storekeepers on manual validation process
7. **Go-Live**: Monitor system behavior and validate business flow

## Rollback Plan

If issues arise, the system can be rolled back by:
1. Disabling Kestedemena mode in POS configurations
2. This will revert to standard Odoo POS behavior
3. No database changes are required for rollback 