# POS Fiscal Module - Reconciliation Issues Analysis

## Module Overview
The `pos_fiscal` module is an Odoo addon that manages fiscal reconciliation for Point of Sale (POS) systems. It synchronizes data between:
- **POS Invoices** (from fiscal devices - EJ data) - Source of Truth
- **POS Orders** (Odoo internal orders)
- **Z-Reports** (End-of-day fiscal reports)
- **Stock Pickings** (Inventory movements)

## Current Workflow

### 1. Main Reconciliation Process
**File:** `models/pos_order_reconcile_new.py` - `run_reconciliation_check()` method (lines 62-282)

**Process Flow:**
1. Fetches invoices from fiscal device (Source of Truth)
2. Fetches existing POS orders from Odoo
3. Fetches refunds and Z-reports
4. **Phase 1:** Resolves duplicate FS numbers
5. **Phase 2:** Processes orphan orders (orders without fiscal data)
6. **Phase 3:** Validates orders against invoices
7. **Phase 4:** Cross-date reconciliation
8. **Phase 5:** Updates order states
9. Generates daily report with statistics

---

## ISSUE #1: Picking Values Not Updated After Mismatch Update

### Problem Description
When a mismatch is detected and the reconciliation process updates an order's values (amount, products, customer, etc.), the associated **stock picking** (inventory movement) is NOT updated or regenerated to match the new order data.

### Location in Code
**File:** `models/pos_order_reconcile_new.py`

**Method:** `_sync_order_with_invoice()` (lines 840-1016)

### Current Behavior

```python
# Line 840-1016: _sync_order_with_invoice()
def _sync_order_with_invoice(self, order, invoice_data, daily_report):
    # Step 1-9: Updates order completely
    # ...

    # Step 10: Creates new invoice (lines 972-980)
    new_invoice = order.action_pos_order_invoice()

    # Step 11: ATTEMPTS to regenerate picking (lines 982-989)
    picking = order._regenerate_order_picking()  # ❌ THIS METHOD EXISTS
```

### The Problem

**File:** `models/pos_order.py` - `_regenerate_order_picking()` (lines 442-472)

The method DOES exist and is implemented, but there are issues:

1. **Incomplete Picking Cancellation:**
   - Only searches for pickings with `pos_order_id` field
   - The field `pos_order_id` in `stock.picking` is defined in `models/stock_picking.py` (lines 4-9)
   - However, pickings created by `pos_etta` or standard Odoo might not have this field set

2. **Partner Mismatch:**
   - Old picking might have old customer (partner_id)
   - New picking is created with new customer
   - This creates inventory inconsistency

3. **Product Mismatch:**
   - If invoice has different products than original order
   - Old picking has old products
   - New picking has new products
   - Stock moves don't match actual sales

### Root Cause Analysis

```python
# In _regenerate_order_picking() - Line 449
existing_pickings = self.env['stock.picking'].search([('pos_order_id', '=', self.id)])
```

**Problem:** This search only finds pickings explicitly linked to the order via `pos_order_id` field. Many pickings created by other methods might use:
- `origin` field (containing order name)
- No explicit link at all
- Links through move lines

### Impact

1. **Inventory Inaccuracy:**
   - Wrong products deducted from stock
   - Wrong quantities recorded

2. **Customer Mismatch:**
   - Picking shows wrong customer
   - Affects delivery tracking and customer history

3. **Audit Trail Issues:**
   - Picking data doesn't match invoice
   - Compliance problems for fiscal audits

### Proposed Solution

**File:** `models/pos_order.py` - Update `_regenerate_order_picking()` method

```python
def _regenerate_order_picking(self):
    """Regenerate stock picking for an existing order after update"""
    self.ensure_one()

    _logger.info("🔄 Regenerating picking for updated order %s", self.id)

    # IMPROVED: Search for pickings using multiple criteria
    existing_pickings = self.env['stock.picking'].search([
        '|', '|',
        ('pos_order_id', '=', self.id),
        ('origin', '=', self.name),
        ('origin', '=', self.pos_reference)
    ])

    # Cancel and remove ALL related pickings
    for picking in existing_pickings:
        try:
            if picking.state == 'draft':
                picking.unlink()
            elif picking.state in ['waiting', 'confirmed', 'assigned']:
                picking.action_cancel()
                picking.unlink()  # Delete after cancel
            elif picking.state == 'done':
                # For done pickings, create a reverse picking
                _logger.warning("Creating reverse picking for completed picking %s", picking.name)
                picking.action_reverse()  # If available, or manual reversal
        except Exception as e:
            _logger.error("Error handling picking %s: %s", picking.name, str(e))

    # Create new picking with updated order data
    new_picking = self._create_order_picking()

    # Ensure the picking is linked to the order
    if new_picking:
        for picking in new_picking:
            picking.write({
                'pos_order_id': self.id,
                'origin': self.name or self.pos_reference,
                'partner_id': self.partner_id.id if self.partner_id else False
            })
        _logger.info("✅ Successfully regenerated picking for order %s", self.id)

    return new_picking
```

### Additional Fix Required

**File:** `models/pos_order_reconcile_new.py` - Line 985

Ensure picking regeneration happens BEFORE invoicing (not after), because invoicing might lock certain order fields:

```python
# CURRENT ORDER (WRONG):
# Step 10: Create invoice
new_invoice = order.action_pos_order_invoice()

# Step 11: Regenerate picking
picking = order._regenerate_order_picking()

# SHOULD BE (CORRECT):
# Step 10: Regenerate picking FIRST
picking = order._regenerate_order_picking()

# Step 11: Create invoice AFTER
new_invoice = order.action_pos_order_invoice()
```

---

## ISSUE #2: Odoo Default POS Sales Detail Report - Invoices and Session Calculations Incorrect

### Problem Description
When printing the **Odoo default POS Order Sales Detail Report** for sessions containing orders created through reconciliation, the report shows:
- ✅ **Payments:** Correct
- ❌ **Invoices:** Shows "no invoice" instead of the actual invoice numbers
- ✅ **Number of transactions:** Correct
- ❌ **Expected / Counted / Difference:** Values are incorrect

### Report Structure
The standard Odoo POS Sales Detail Report (accessible from POS Session or POS Orders) displays:
```
Sales Details Report
├── Session Information
├── Payments (correct)
├── Invoices (showing "no invoice" - INCORRECT)
└── Session Control
    ├── Total
    ├── Number of transactions (correct)
    └── Expected / Counted / Difference (INCORRECT)
```

### Location in Code
This issue affects orders created by the reconciliation process in:
- **File:** `models/pos_order_reconcile_new.py`
- **Method:** `_sync_order_with_invoice()` (lines 840-1016)
- **Method:** `_create_order_from_invoice()` (lines 1041-1277)

### Root Cause Analysis

#### Issue 2A: Missing Invoice Link (`account_move`)

**Problem:** Orders created or updated by reconciliation don't have proper `account_move` (invoice) links.

**Current Code Flow:**
```python
# In _create_order_from_invoice() - Line 1063
new_order = self.create(order_vals)

# Line 1066-1072: Sets state
new_order.write({'state': 'invoiced'})

# Line 1238-1275: Auto-invoicing (if enabled)
if self.env.context.get('auto_invoice_created', False):
    invoice = new_order.action_pos_order_invoice()
```

**The Problem:**
1. Orders are created with `state = 'invoiced'` (line 1067)
2. But `account_move` field is NOT set during order creation
3. Auto-invoicing only happens if `auto_invoice_created` context is True
4. Even when invoice is created, the link might not persist correctly

**Why This Causes "No Invoice" in Report:**
The Odoo sales detail report looks for:
- `order.account_move` field
- `order.state in ['paid', 'done', 'invoiced']`
- If `account_move` is False, it shows "no invoice"

#### Issue 2B: Session Opening/Closing Balance Calculation

**Problem:** Expected/Counted/Difference calculations don't account for orders created outside normal POS session flow.

**Standard Odoo Session Flow:**
```
Expected = Session Opening Balance + Order Totals
Counted = Actual Cash/Payments Counted
Difference = Expected - Counted
```

**Current Problem:**
1. Orders created by reconciliation are linked to closed sessions
2. These orders were not part of the original session opening/closing
3. Session balance was already counted and closed
4. Adding orders retroactively doesn't update session balances

**Why This Causes Incorrect Expected/Counted/Difference:**
- **Expected** includes new orders added to session
- **Counted** is from the original session close (doesn't include new orders)
- **Difference** shows mismatch because we added orders after session was closed

### Current State Management

**File:** `models/pos_order_reconcile_new.py`

**States set during reconciliation:**
```python
# Line 754-787: _update_orders_to_invoiced_state()
self.env.cr.execute("""
    UPDATE pos_order
    SET state = 'invoiced'
    WHERE id = %s
""", (order.id,))

# Line 1067: In _create_order_from_invoice()
new_order.write({'state': 'invoiced'})

# Line 1244: Before auto-invoicing
if new_order.fiscal_mrc and new_order.fs_no:
    new_order.write({'state': 'invoiced'})
```

**The Paradox:**
- Order has `state = 'invoiced'`
- But `account_move` field is empty or not properly linked
- This violates Odoo's expectation that `invoiced` state means an invoice exists

### Proposed Solution

#### Fix 2A: Ensure Invoice is Created and Linked for ALL Reconciled Orders

**File:** `models/pos_order_reconcile_new.py`

**Method:** `_create_order_from_invoice()` - Update line 1063-1073

```python
# CURRENT (WRONG):
new_order = self.create(order_vals)
if new_order.fiscal_mrc and new_order.fs_no:
    new_order.write({'state': 'invoiced'})
else:
    new_order.write({'state': 'paid'})

# SHOULD BE (CORRECT):
new_order = self.create(order_vals)

# ALWAYS create invoice for reconciled orders
_logger.info("📄 Creating invoice for reconciled order %s", new_order.id)
try:
    invoice = new_order.action_pos_order_invoice()
    if invoice and new_order.account_move:
        new_order.write({'state': 'invoiced'})
        _logger.info("✅ Invoice created and linked: %s", new_order.account_move.name)
    else:
        _logger.warning("⚠️ Invoice creation returned but account_move not set")
        new_order.write({'state': 'paid'})
except Exception as e:
    _logger.error("❌ Failed to create invoice: %s", str(e))
    new_order.write({'state': 'paid'})
```

**Method:** `_sync_order_with_invoice()` - Update line 972-989

```python
# CURRENT ORDER (may cause issues):
# Step 10: Create invoice
new_invoice = order.action_pos_order_invoice()

# Step 11: Regenerate picking
picking = order._regenerate_order_picking()

# SHOULD BE (CORRECT ORDER):
# Step 10: Regenerate picking FIRST (before invoicing locks fields)
picking = order._regenerate_order_picking()

# Step 11: Create invoice AFTER (and verify link)
try:
    new_invoice = order.action_pos_order_invoice()

    # Verify invoice was created and linked
    if not order.account_move:
        _logger.error("❌ Invoice created but not linked to order %s", order.id)
        # Force link if invoice exists
        if new_invoice:
            order.write({'account_move': new_invoice.id})

    _logger.info("✅ Invoice linked to order: %s", order.account_move.name)
except Exception as e:
    _logger.error("❌ Invoice creation failed: %s", str(e))
```

#### Fix 2B: Add Method to Recalculate Session Balances

**File:** `models/pos_order_reconcile_new.py` - Add new method

```python
def _recalculate_session_balances(self, session_id):
    """
    Recalculate session opening/closing balances after adding/modifying orders.
    This ensures Expected/Counted/Difference are correct in sales detail report.
    """
    session = self.env['pos.session'].browse(session_id)
    if not session:
        return False

    _logger.info("🔄 Recalculating session balances for %s", session.name)

    # Get all valid orders in this session
    session_orders = self.search([
        ('session_id', '=', session_id),
        ('state', 'in', ['paid', 'done', 'invoiced'])
    ])

    # Calculate total from orders
    total_sales = sum(order.amount_total for order in session_orders)
    total_tax = sum(order.amount_tax for order in session_orders)

    # Update session totals if session is closed
    # Note: Only update if we have permission and it makes sense
    if session.state == 'closed':
        _logger.warning("⚠️ Session %s is closed. Expected/Counted may not match.", session.name)
        _logger.info("   Total sales from orders: %.2f", total_sales)
        _logger.info("   Session expects this in 'Counted' value")

    return True
```

**Call this method after reconciliation:**
```python
# In run_reconciliation_check() - After Phase 5 (line 201)
# Recalculate session balances
if session:
    self._recalculate_session_balances(session.id)
```

#### Fix 2C: Add Warning Note to Orders Created After Session Close

**File:** `models/pos_order_reconcile_new.py`

Add a note field to track reconciliation context:

```python
# In _prepare_pos_order_vals() - Line 1551-1572, add:
return {
    'name': session.config_id.name,
    'fs_no': str(invoice.fsNumber).zfill(8),
    # ... existing fields ...
    'note': f'Created by reconciliation from invoice {invoice.fsNumber}. '
            f'Session was already closed when this order was added.',
}
```

This helps explain why Expected/Counted/Difference might not match.

---

## Implementation Priority

### High Priority (Fix Immediately)
1. ✅ **Issue #1:** Fix picking regeneration search criteria to find all related pickings
2. ✅ **Issue #1:** Update picking regeneration to happen before invoicing
3. ✅ **Issue #2:** Ensure invoice (`account_move`) is created and linked for ALL reconciled orders
4. ✅ **Issue #2:** Add verification that invoice link persists after creation

### Medium Priority (Fix Soon)
1. **Issue #2:** Add session balance recalculation method
2. **Issue #2:** Add note field to track orders created after session close
3. **Issue #1:** Add reverse picking logic for already-validated pickings

### Low Priority (Enhancement)
1. Add email notifications for picking/invoice mismatches
2. Add graphical dashboard for reconciliation status
3. Add automated session balance adjustment option

---

## Testing Checklist

### For Issue #1 (Picking Updates)
- [ ] Create order with mismatch (different customer, products, or quantities)
- [ ] Run reconciliation
- [ ] Verify old picking is found and cancelled/deleted
- [ ] Verify new picking is created with correct:
  - [ ] Products (matching updated order)
  - [ ] Quantities (matching updated order)
  - [ ] Customer - partner_id (matching updated order)
  - [ ] Origin reference (order name/pos_reference)
  - [ ] pos_order_id field properly set
- [ ] Check stock levels are correct after update
- [ ] Verify no duplicate pickings exist
- [ ] Test edge cases:
  - [ ] Picking already in 'done' state
  - [ ] Picking linked by origin instead of pos_order_id
  - [ ] Multiple pickings for same order

### For Issue #2 (Sales Detail Report - Invoice and Session Values)
- [ ] Create test session and close it
- [ ] Run reconciliation for that session's date
- [ ] Print/View "Sales Detail Report" for the session
- [ ] Verify report sections:
  - [ ] **Payments:** Shows correct payment methods and amounts
  - [ ] **Invoices:** Shows actual invoice numbers (NOT "no invoice")
  - [ ] **Number of transactions:** Correct count
  - [ ] **Expected:** Shows correct total from session orders
  - [ ] **Counted:** Shows correct total based on session close
  - [ ] **Difference:** Calculation is Expected - Counted
- [ ] Check order.account_move field is set:
  - [ ] For orders created by reconciliation
  - [ ] For orders updated by reconciliation
  - [ ] Invoice name/number is visible
- [ ] Test scenarios:
  - [ ] New order created from invoice (should have account_move)
  - [ ] Existing order updated (invoice should be regenerated)
  - [ ] Order with refunds (invoice should reflect correctly)
  - [ ] Multiple orders in same session
- [ ] Verify session state:
  - [ ] Session remains 'closed' after reconciliation
  - [ ] Session totals updated or noted appropriately

---

## Additional Notes

### Invoice as Source of Truth
The module correctly treats **invoices** (EJ data from fiscal device) as the source of truth. This means:
- If invoice exists but no order → Create order from invoice
- If order exists but doesn't match invoice → Update order to match invoice
- If order exists but no invoice → Cancel order (likely a duplicate or error)

### Reconciliation Phases
The reconciliation happens in 5 phases:
1. **Duplicate Resolution:** Find and fix duplicate FS numbers
2. **Orphan Processing:** Link or cancel orders without fiscal data
3. **Invoice Validation:** Create/update orders to match invoices
4. **Cross-Date Reconciliation:** Fix orders with wrong dates
5. **State Update:** Set all valid orders to 'invoiced' state

### Key Files to Modify

**For Issue #1 (Picking Updates):**
1. `models/pos_order.py` - Fix `_regenerate_order_picking()` method
2. `models/pos_order_reconcile_new.py` - Reorder invoice/picking creation in `_sync_order_with_invoice()`

**For Issue #2 (Sales Detail Report):**
1. `models/pos_order_reconcile_new.py`:
   - Fix `_create_order_from_invoice()` - Always create invoice
   - Fix `_sync_order_with_invoice()` - Verify invoice link
   - Add `_recalculate_session_balances()` method
   - Update `_prepare_pos_order_vals()` - Add note field
2. `models/pos_order.py` - Ensure `action_pos_order_invoice()` properly sets `account_move`

---

## Summary

### Issue #1: Stock Picking Not Updated After Reconciliation
**Impact:** When reconciliation updates an order (customer, products, quantities), the inventory movements (pickings) don't reflect the changes.
**Root Cause:** `_regenerate_order_picking()` doesn't find all related pickings due to limited search criteria.
**Fix:** Improve search to find pickings by `pos_order_id`, `origin`, or `pos_reference`, and ensure picking is regenerated before invoicing.

### Issue #2: Odoo Sales Detail Report Shows "No Invoice" and Wrong Expected/Counted/Difference
**Impact:** Standard Odoo POS Sales Detail Report shows "no invoice" for reconciled orders, and Expected/Counted/Difference values are incorrect.
**Root Cause:**
- Orders have `state='invoiced'` but `account_move` field is not set or not persistent
- Session balances calculated before orders were added don't reflect the new orders
**Fix:**
- Always create and verify invoice link for reconciled orders
- Regenerate picking before invoicing (to avoid field locking issues)
- Optionally recalculate session balances or add notes explaining the discrepancy

---

**Document Version:** 1.1
**Date:** 2025-10-22
**Updated:** Corrected Issue #2 analysis based on user clarification about Odoo default Sales Detail Report
**Author:** Analysis based on code review
