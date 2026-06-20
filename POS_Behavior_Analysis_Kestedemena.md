# POS Behavior Analysis for Kestedemena Business Requirements

## Current Issues Identified

Based on the analysis of the custom-addons codebase, the following issues need to be addressed to align with Kestedemena's business flow:

### 1. Sales Order Cancellation Issue
**Problem**: When payment is processed in POS, the system cancels previously confirmed sales orders.

**File Location**: The core issue is likely in the standard Odoo POS module, but the custom behavior is controlled in:
- `pos_etta/models/pos_orderline.py` - Lines 120-150 (in `_process_order` method)

### 2. Immediate Stock Deduction Issue
**Problem**: Stock is immediately deducted when products are sold directly through POS.

**File Locations**:
- `pos_etta/models/bi_pos_stock.py` - Lines 228-281 (in `_create_picking_from_pos_order_lines` method)
- `pos_etta/models/pos_orderline.py` - Lines 120-150 (in `_process_order` method)

### 3. Delivery Order Creation Issue
**Problem**: Delivery orders are marked as "Done" immediately instead of "Ready" for manual validation.

**File Location**:
- `pos_etta/models/bi_pos_stock.py` - Lines 248-252 (delivery order state management)

## Required Changes

### 1. Prevent Sales Order Cancellation
**File**: `pos_etta/models/pos_orderline.py`
**Method**: `_process_order`
**Current Behavior**: Calls `super()._process_order()` which may cancel sales orders
**Required Change**: Override the sales order handling to keep orders active

### 2. Modify Stock Movement Behavior
**File**: `pos_etta/models/bi_pos_stock.py`
**Method**: `_create_picking_from_pos_order_lines`
**Current Behavior**: 
- Lines 248-252: Creates delivery orders and marks them as "waiting"
- Lines 260-270: Handles negative lines (returns)
**Required Change**: 
- Create delivery orders in "Ready" state instead of "Done"
- Prevent immediate stock deduction
- Allow manual validation by storekeeper

### 3. Add Configuration Options
**File**: `pos_etta/models/pos_config.py`
**Current Fields**: Lines 1-214 (various configuration options)
**Required Addition**: 
- Add fields to control Kestedemena-specific behavior
- Add options for delivery order state management
- Add options for stock movement timing

## Detailed Code Analysis

### Current Stock Movement Logic
```python
# In pos_etta/models/bi_pos_stock.py - Lines 248-252
try:
    with self.env.cr.savepoint():
       positive_picking.action_confirm()
       positive_picking.write({'state': 'waiting'})  
except (UserError, ValidationError):
    pass
```

**Issue**: The delivery order is created and confirmed, but should remain in "Ready" state for manual validation.

### Current Order Processing Logic
```python
# In pos_etta/models/pos_orderline.py - Lines 120-150
@api.model
def _process_order(self, order, draft, existing_order):
    result = super(PosOrderInherit, self)._process_order(order, draft, existing_order)
    # ... MRP order creation logic
    return result
```

**Issue**: The `super()._process_order()` call may trigger sales order cancellation in the standard Odoo behavior.

## Recommended Solution Structure

### 1. Create New Configuration Fields
Add to `pos_etta/models/pos_config.py`:
```python
# Kestedemena-specific configuration
kestedemena_mode = fields.Boolean("Kestedemena Business Mode", default=False)
delivery_order_state = fields.Selection([
    ('ready', 'Ready for Manual Validation'),
    ('done', 'Done (Immediate)')
], string='Delivery Order State', default='ready')
prevent_stock_deduction = fields.Boolean("Prevent Immediate Stock Deduction", default=True)
```

### 2. Modify Stock Movement Logic
Update `pos_etta/models/bi_pos_stock.py`:
```python
# In _create_picking_from_pos_order_lines method
if pos_order.config_id.kestedemena_mode:
    # Create delivery order in Ready state
    positive_picking.write({'state': 'ready'})
    # Don't deduct stock immediately
else:
    # Standard behavior
    positive_picking.action_confirm()
    positive_picking.write({'state': 'waiting'})
```

### 3. Override Sales Order Processing
Update `pos_etta/models/pos_orderline.py`:
```python
# In _process_order method
if pos_order.config_id.kestedemena_mode:
    # Prevent sales order cancellation
    # Keep sales order in confirmed state
    # Create delivery order in Ready state
else:
    # Standard behavior
    result = super(PosOrderInherit, self)._process_order(order, draft, existing_order)
```

## Implementation Priority

1. **High Priority**: Modify `bi_pos_stock.py` to create delivery orders in "Ready" state
2. **High Priority**: Add configuration options in `pos_config.py`
3. **Medium Priority**: Override sales order processing in `pos_orderline.py`
4. **Low Priority**: Add UI controls for storekeeper validation

## Testing Scenarios

1. **Sales Order → POS**: Verify sales order remains confirmed, delivery order created in Ready state
2. **Direct POS Sale**: Verify delivery order created in Ready state, no immediate stock deduction
3. **Manual Validation**: Verify storekeeper can manually validate delivery orders
4. **Configuration**: Verify Kestedemena mode can be enabled/disabled per POS configuration

## Files to Modify

1. `pos_etta/models/pos_config.py` - Add configuration fields
2. `pos_etta/models/bi_pos_stock.py` - Modify delivery order creation logic
3. `pos_etta/models/pos_orderline.py` - Override order processing
4. `pos_etta/views/pos_config_views.xml` - Add UI for new configuration options
5. `pos_etta/static/src/app/` - Add frontend controls if needed

This analysis provides the complete roadmap for implementing Kestedemena's business requirements in the POS system. 