# Reconciliation Update Specification - Existing Order Update

## Overview
This document outlines the requirements for updating existing POS orders during reconciliation to ensure COMPLETE synchronization of ALL data fields from POS Invoices (fiscal system) to POS Orders (Odoo system).

## Current Issue
The reconciliation process currently updates only some fields when matching invoices with existing orders. This causes data inconsistencies where orders don't fully reflect the fiscal reality captured in the invoice system. We need to update ALL fields including order lines (products), payments, customer info, and all financial data.

## Scenario: Existing Order Update

When an order exists with a matching FS number during reconciliation, the system must:

### 1. Complete Field Synchronization

#### Core Order Fields to Update
```python
{
    'name': session.config_id.name,
    'fs_no': str(invoice.fsNumber).zfill(8),
    'fiscal_mrc': fiscal_mrc,
    'ej_checksum': invoice.checksum,
    'pos_reference': invoice.referenceNumber,
    'amount_total': invoice.totalWithTax,
    'amount_tax': invoice.totalTax or 0.0,
    'amount_paid': invoice.totalPaid or invoice.totalWithTax,
    'amount_return': invoice.change or 0.0,
    'date_order': order_datetime,  # Combined date/time
    'partner_id': partner_id,  # Lookup or create from buyerName
    'session_id': session_id,  # Keep existing or find appropriate
    'company_id': company_id,
    'employee_id': employee_id,  # Lookup from cashierName
}
```

#### Order Lines - Complete Replacement
The existing order lines must be REPLACED with invoice lines data:

```python
order_lines.append((0, 0, {
    'product_id': product.id,
    'full_product_name': product.name or line.itemName,
    'qty': line.quantity,
    'price_unit': price_unit_without_tax,
    'price_subtotal': line.lineTotal,
    'price_subtotal_incl': line.lineTotalWithTax,
    'tax_ids': [(6, 0, tax_ids)] if tax_ids else False,
}))
```

#### Payment Methods - Complete Replacement
The existing payment records must be REPLACED with invoice payment data:

```python
'payment_ids': [(0, 0, {
    'payment_method_id': payment_method_id,
    'amount': amount_paid,  # Should equal totalWithTax
    'payment_date': order_datetime,  # Combined date/time
})]
```

### 2. Implementation Steps

#### Step 1: Delete Existing Lines and Payments
Before updating, clear existing data to avoid duplicates:
```python
# Delete existing order lines
order.lines.unlink()

# Delete existing payment records  
order.payment_ids.unlink()
```

#### Step 2: Prepare Complete Order Data
Use the same logic as order creation but for update:
```python
# Get invoice record
invoice_rec = self.env['pos.invoice'].browse(invoice_data['id'])

# Find or keep session
if not order.session_id:
    session = self._find_or_create_session(target_mrc, invoice_date)
else:
    session = order.session_id

# Prepare complete order values using existing method
order_vals = self._prepare_pos_order_vals(invoice_rec, target_mrc, session.id)
```

#### Step 3: Update Order with ALL Fields
```python
# Extract lines and payments for special handling
lines_data = order_vals.pop('lines', [])
payment_data = order_vals.pop('payment_ids', [])

# Update core order fields
order.write(order_vals)

# Create new lines
for line in lines_data:
    order.lines.create(line[2])  # line[2] contains the dict

# Create new payments
for payment in payment_data:
    order.payment_ids.create(payment[2])  # payment[2] contains the dict
```

### 3. Implementation Details

#### Enhanced `_sync_order_with_invoice` Method

```python
def _sync_order_with_invoice(self, order, invoice_data, daily_report):
    """
    Complete synchronization of ALL invoice fields to existing order.
    This method completely replaces order data with invoice data.
    """
    try:
        # Log the update attempt
        _logger.info("🔄 Starting complete sync for order %s with invoice FS %s", 
                    order.id, invoice_data['fsNumber'])
        
        # Store old values for logging
        old_amount = order.amount_total
        old_lines_count = len(order.lines)
        old_payment_count = len(order.payment_ids)
        
        # Get invoice record for complete data
        invoice_rec = self.env['pos.invoice'].browse(invoice_data['id'])
        
        # Determine session
        if not order.session_id:
            invoice_date = fields.Datetime.from_string(invoice_data['date']).date()
            session = self._find_or_create_session(order.fiscal_mrc or invoice_rec.device_id.mrc, invoice_date)
        else:
            session = order.session_id
        
        if not session:
            _logger.error("❌ Cannot find session for order update")
            return False
        
        # Prepare COMPLETE order values using existing method
        order_vals = self._prepare_pos_order_vals(
            invoice_rec, 
            order.fiscal_mrc or invoice_rec.device_id.mrc,
            session.id
        )
        
        if not order_vals:
            _logger.error("❌ Cannot prepare order values for update")
            return False
        
        # Step 1: Clear existing lines and payments
        _logger.info("🗑️ Clearing existing lines (%d) and payments (%d)", 
                    old_lines_count, old_payment_count)
        order.lines.unlink()
        order.payment_ids.unlink()
        
        # Step 2: Extract lines and payments for special handling
        lines_data = order_vals.pop('lines', [])
        payment_data = order_vals.pop('payment_ids', [])
        
        # Step 3: Update core order fields
        _logger.info("📝 Updating core order fields")
        order.write(order_vals)
        
        # Step 4: Create new lines from invoice
        _logger.info("➕ Creating %d new order lines from invoice", len(lines_data))
        for line_tuple in lines_data:
            # line_tuple is (0, 0, dict)
            line_vals = line_tuple[2]
            line_vals['order_id'] = order.id
            order.lines.create(line_vals)
        
        # Step 5: Create new payments from invoice
        _logger.info("💳 Creating %d new payment(s) from invoice", len(payment_data))
        for payment_tuple in payment_data:
            # payment_tuple is (0, 0, dict)
            payment_vals = payment_tuple[2]
            payment_vals['pos_order_id'] = order.id
            order.payment_ids.create(payment_vals)
        
        # Step 6: Recompute totals
        order._compute_total_cost_in_real_time()
        
        # Step 7: Log the complete update
        self.env['pos.change.log'].log_change(
            pos_order_id=order.id,
            fs_no=str(invoice_data['fsNumber']).zfill(8),
            fiscal_mrc=order.fiscal_mrc,
            change_type='complete_update',
            old_value=f'amount: {old_amount:.2f}, lines: {old_lines_count}, payments: {old_payment_count}',
            new_value=f'amount: {order.amount_total:.2f}, lines: {len(order.lines)}, payments: {len(order.payment_ids)}',
            daily_report_id=daily_report.id
        )
        
        _logger.info("✅ Complete sync successful for order %s", order.id)
        return True
        
    except Exception as e:
        _logger.error("❌ Failed to sync order %s: %s", order.id, str(e))
        return False
```

### 4. Key Points for Implementation

1. **Complete Data Replacement**: The update process completely replaces existing order data with invoice data
2. **Use Existing Methods**: Leverage the `_prepare_pos_order_vals` method that's already used for order creation
3. **Maintain Data Integrity**: Ensure all relationships (session, partner, employee) are properly maintained
4. **Product Matching**: Use the same product matching logic as order creation (PLU code, name matching)
5. **Tax Handling**: Properly handle tax configuration from products
6. **Logging**: Comprehensive logging of all changes for audit trail

### 5. Testing Requirements

#### Test Cases

1. **Complete Update Test**
   - Create an order with minimal data
   - Run reconciliation with matching invoice
   - Verify ALL fields are updated:
     - Financial totals (amount_total, amount_tax, amount_paid)
     - Reference fields (fs_no, pos_reference, ej_checksum)
     - Date and time
     - Partner information
     - Employee information
     - All order lines replaced
     - All payments replaced

2. **Order Lines Replacement Test**
   - Create order with 3 products
   - Invoice has 5 different products
   - After sync, order should have exactly 5 products from invoice
   - Verify quantities, prices, taxes match invoice

3. **Payment Replacement Test**
   - Order has cash payment
   - Invoice has card payment
   - After sync, order should have card payment with invoice amount

4. **Product Matching Test**
   - Test PLU code matching
   - Test name matching (exact and partial)
   - Test tax configuration from products

### 6. Example Usage

```python
# During reconciliation, when order exists with matching FS
existing_order = self.search([
    ('fs_no', '=', invoice_fs_number),
    ('fiscal_mrc', '=', target_mrc)
], limit=1)

if existing_order:
    # Complete update from invoice
    success = self._sync_order_with_invoice(existing_order, invoice_data, daily_report)
    if success:
        _logger.info("✅ Order %s fully synchronized with invoice FS %s", 
                    existing_order.id, invoice_fs_number)
    else:
        _logger.error("❌ Failed to sync order %s", existing_order.id)
```

## Success Criteria

- Existing orders are COMPLETELY updated with ALL invoice data
- Order lines are replaced, not merged
- Payments are replaced, not merged  
- All financial totals match invoice exactly
- Complete audit trail via change logs
- No data inconsistencies after reconciliation