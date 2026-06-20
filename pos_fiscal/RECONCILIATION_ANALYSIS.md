# POS Fiscal Reconciliation Analysis
## Complete Checkup/Comparison List

**Generated:** 2025-12-11

---

## 📊 Reconciliation Architecture Overview

```
RECONCILIATION PROCESS FLOW
════════════════════════════════════════════════════════════════════

INPUT DATA SOURCES
├── pos.order (POS Orders)
├── pos.invoice (Fiscal Invoices - EJ Data) ← SOURCE OF TRUTH
├── pos.refund (Refund Records)
└── pos.zreport (Daily Z-Reports)

        ↓

DATA VALIDATION & COMPARISON (3 Phases)
├── Phase 1: Duplicate Resolution
├── Phase 2: Orphan Processing
└── Phase 3: Invoice-Based Validation & Sync

        ↓

OUTPUT RESULTS
├── pos.daily.report (Summary Report)
├── pos.change.log (Audit Trail)
└── Updated pos.order records
```

---

## 🔍 PHASE 1: DUPLICATE RESOLUTION

### Purpose
Find and resolve multiple POS orders with the same FS number.

### Checkup Steps

#### 1.1 Identify Duplicate FS Numbers
```python
# Find all FS numbers with count > 1
Groups = pos.order.read_group([
    ('fs_no', '!=', False),
    ('fiscal_mrc', '=', target_mrc),
    ('date_order', '>=', start_date),
    ('date_order', '<=', end_date),
    ('state', 'in', ['paid', 'done'])
], groupby=['fs_no'], lazy=False)

# Result: List of groups with __count > 1
```

**Comparison Points:**
- ✅ Same FS number
- ✅ Same MRC
- ✅ Within date range
- ✅ Order states: 'paid' or 'done'

#### 1.2 Match Each Duplicate Group to Invoice

For each duplicate group, find the invoice with matching FS number:

```python
fs_key = standardize_fs_number(fs_no)
invoice_data = invoice_map.get(fs_key)
```

**Comparison Points:**
- ✅ Invoice FS number matches (with format standardization)
- ✅ Invoice data exists in source of truth

#### 1.3 Score Orders Against Invoice

For each order in the duplicate group:

```python
score = 0
# Amount Match (Highest Priority)
if abs(order.amount_total - invoice.totalWithTax) < 0.01:
    score += 100  # Exact match
elif abs(order.amount_total - invoice.totalWithTax) < 1.0:
    score += 50   # Close match
elif abs(order.amount_total - invoice.totalWithTax) < 10.0:
    score += 10   # Reasonable match

# Date Match
if order.date_order.date() == invoice.date:
    score += 20

# Reference Number Match
if order.pos_reference == invoice.referenceNumber:
    score += 30

# Data Completeness
if order.partner_id:
    score += 5
if order.payment_ids:
    score += 5
```

**Comparison Metrics:**
- 🔢 Amount difference (primary)
- 📅 Date matching (secondary)
- 🏷️ Reference number (tertiary)
- 👥 Data completeness (tie-breaker)

#### 1.4 Decision Making

```
IF invoice_found:
    IF best_match found (score >= 50):
        → Keep best_match
        → Cancel all others
        → Sync best_match with invoice data
    ELSE:
        → Cancel all orders
        → Mark for re-creation from invoice
ELSE:
    → Keep first order only
    → Cancel remaining duplicates
```

### Result Metrics
- `duplicates_found` - Count of duplicate FS groups
- `duplicates_resolved` - Count of groups processed
- `orders_cancelled` - Count of orders cancelled (from duplicates)

---

## 🔗 PHASE 2: ORPHAN ORDER PROCESSING

### Purpose
Find orders without fiscal_mrc or fs_no and link them to invoices or cancel them.

### Checkup Steps

#### 2.1 Identify Orphan Orders

```python
orphan_orders = pos.order.search([
    '|',
    ('fiscal_mrc', '=', False),
    ('fs_no', '=', False),
    ('date_order', '>=', start_date),
    ('date_order', '<=', end_date),
    ('state', 'in', ['paid', 'done']),
])
```

**Comparison Points:**
- ✅ Missing fiscal_mrc OR missing fs_no
- ✅ Paid or done status
- ✅ Within date range

#### 2.2 Match Orphan to Invoice by Reference

For each orphan order:

```python
IF order.pos_reference:
    FOR invoice IN invoices:
        IF order.pos_reference == invoice.referenceNumber:
            → Link orphan to invoice
            → Sync with invoice data
            → Mark as resolved
ELSE:
    → Cancel orphan (no matching invoice found)
```

**Comparison Points:**
- 🏷️ POS reference number matches invoice reference number
- ✅ Invoice exists in source of truth
- ✅ Reference number format consistency

#### 2.3 Sync Orphan with Invoice

```python
order.write({
    'fiscal_mrc': target_mrc,
    'fs_no': formatted_invoice_fs_number,
    'amount_total': invoice.totalWithTax,
    'amount_tax': invoice.totalTax,
    'amount_paid': invoice.totalPaid,
    'amount_return': invoice.change,
})
```

### Result Metrics
- `orphans_linked` - Count of orphans linked to invoices
- `orphans_cancelled` - Count of orphans cancelled (no match)

---

## ✅ PHASE 3: INVOICE-BASED VALIDATION & SYNCHRONIZATION

### Purpose
Ensure every invoice has a corresponding POS order with synchronized data.

### Checkup Steps

#### 3.1 Process Each Invoice

For each invoice in the source of truth:

```python
FOR invoice IN invoice_map:
    existing_order = order_map.get(invoice.fs_key)

    IF existing_order:
        IF needs_update(existing_order, invoice):
            → Sync order with invoice
            → Update inventory (if configured)
            → Update accounting (if configured)
        ELSE:
            → No action needed
    ELSE:
        → Create new order from invoice
        → Create inventory picking (if configured)
        → Auto-invoice order (if configured)
```

#### 3.2 Format Variations Check

For orders without a match, check multiple FS format variations:

```python
fs_variations = [
    str(fs_key),           # Numeric
    str(fs_key).zfill(8),  # Padded (00000001)
    str(fs_key).lstrip('0') # Stripped (1)
]

FOR variation IN fs_variations:
    existing_order = pos.order.search([
        ('fs_no', '=', variation),
        ('fiscal_mrc', '=', target_mrc),
        ('state', '!=', 'cancel')
    ])
```

**Comparison Points:**
- ✅ FS number matching (with format tolerance)
- ✅ MRC matching
- ✅ Not cancelled

#### 3.3 Update Decision Logic

```python
def needs_update(order, invoice):
    # Amount mismatch
    if abs(order.amount_total - invoice.totalWithTax) > 0.01:
        return True

    # Missing fiscal data
    if not order.fs_no or not order.fiscal_mrc:
        return True

    # Payment method mismatch
    if order.payment_ids:
        if order.payment_ids[0].payment_method_id.name != invoice.paymentType:
            return True

    return False
```

#### 3.4 Order Synchronization

```python
order.write({
    'amount_total': invoice.totalWithTax,
    'amount_tax': invoice.totalTax,
    'amount_paid': invoice.totalPaid,
    'amount_return': invoice.change,
    'fs_no': formatted_fs_number,
    'pos_reference': invoice.referenceNumber,
})

# Update payment method if needed
if payment_method_found:
    order.payment_ids[0].write({
        'payment_method_id': payment_method_id,
        'amount': invoice.totalWithTax,
    })
```

#### 3.5 Inventory Picking Creation (if enabled)

```python
IF context.get('create_inventory_picking'):
    IF amount_changed AND not order.picking_ids:
        → Create stock picking via _create_order_picking()
        → Prevents double inventory deduction
```

#### 3.6 Auto-Invoicing (if enabled)

```python
IF context.get('auto_invoice_created'):
    IF order.partner_id:
        → Set order.to_invoice = True
        → Call order.action_pos_order_invoice()
        → Post account.move if created
```

#### 3.7 New Order Creation (if no match)

For invoices without matching orders:

```python
IF not existing_order:
    → Find or create session for invoice date
    → Prepare order values from invoice data
    → Create new pos.order record
    → Create inventory picking (if configured)
    → Auto-invoice order (if configured)
    → Log the creation
```

### Result Metrics
- `orders_created` - New orders created from invoices
- `orders_updated` - Existing orders synced with invoice data
- `unmatched` - Invoices without orders (creation failed)

---

## 📈 PHASE 4: FINAL COMPARISON & VALIDATION

### Purpose
Compare final POS orders against fiscal Z-Reports and invoices.

### Checkup Steps

#### 4.1 Count Matching

```python
updated_orders = pos.order.search([
    ('fiscal_mrc', '=', target_mrc),
    ('date_order', '>=', start_date),
    ('date_order', '<=', end_date),
    ('state', '!=', 'cancel')
])

count_match = len(updated_orders) == invoice_count
```

**Result:** ✅ or ❌ `count_match`

#### 4.2 Amount Totaling

```python
# POS Orders Total
order_total = sum(order.amount_total for order in updated_orders)

# Invoices Total
invoice_total = sum(invoice.totalWithTax for invoice in pos_invoices)

# Refunds Total
refund_total = sum(refund.totalWithTax for refund in pos_refunds)

# Z-Report Total
z_sales_total = sum(zreport.salesTotal for zreport in zreports)
z_refund_total = sum(zreport.rfdSalesTotal for zreport in zreports)

# Net Totals
net_order_total = order_total - refund_total
net_invoice_total = invoice_total - refund_total
net_zreport_total = z_sales_total - z_refund_total
```

#### 4.3 Total Matching

```python
total_mismatch = abs(net_order_total - net_zreport_total)
total_match = total_mismatch <= 0.01
```

**Result:** ✅ or ❌ `total_match`

### Comparison Matrix

| Comparison | Field 1 | Field 2 | Tolerance | Required |
|------------|---------|---------|-----------|----------|
| Count | updated_orders | invoices | Exact | ✅ Yes |
| Sales Total | orders | invoices | ≤ 0.01 | ✅ Yes |
| Sales Total | orders | z-report | ≤ 0.01 | ✅ Yes |
| Net Sales | (order - refund) | (zreport - refund) | ≤ 0.01 | ✅ Yes |
| Payment Method | order | invoice | Exact | ⚠️ Conditional |
| Date | order | invoice | ±1 day | ⚠️ Conditional |

---

## 📋 CLEANUP: UNRECONCILED ORDERS

### Purpose
Cancel any orders that don't have fiscal data after reconciliation.

### Checkup Steps

```python
unreconciled_orders = pos.order.search([
    ('fiscal_mrc', 'in', [False, '']),
    ('fs_no', 'in', [False, '']),
    ('date_order', '>=', start_date),
    ('date_order', '<=', end_date),
])

# Cancel all unreconciled orders
FOR order IN unreconciled_orders:
    → Cancel order
    → Log cancellation
```

---

## 📊 FINAL RECONCILIATION REPORT

### Daily Report Fields

| Field | Source | Purpose |
|-------|--------|---------|
| `pos_order_count` | Updated orders | Final order count |
| `invoice_count` | Source data | Total invoices processed |
| `refund_count` | Source data | Total refunds |
| `unmatched_fs_count` | Failed creations | Invoices without orders |
| `session_total` | Sum of orders | Total POS sales |
| `z_report_total` | Sum of z-reports | Total fiscal device sales |
| `refund_total` | Sum of refunds | Total refunds |
| `net_order_total` | Orders - Refunds | Net POS sales |
| `net_invoice_total` | Invoices - Refunds | Net fiscal sales |
| `net_zreport_total` | Z-Report - Refunds | Net device sales |
| `total_mismatch` | Absolute difference | Order vs Device mismatch |
| `recreated_orders` | Created from invoices | New order count |
| `updated_orders` | Synced from invoices | Updated order count |
| `cancelled_orders` | Cancelled during reconciliation | Removed order count |

### Summary Metrics Logged

```
════════════════════════════════════════════════════
📊 RECONCILIATION SUMMARY
════════════════════════════════════════════════════
📦 Orders: X | Invoices: Y | Refunds: Z
💸 Totals - Order: A.XX | Invoice: B.XX | Z-Report: C.XX
🔄 Changes - Created: P | Updated: Q | Cancelled: R
🔗 Duplicates: S found, T resolved | Orphans linked: U
⏱️ Processing time: V.VV seconds
════════════════════════════════════════════════════
```

### Status Indicators

| Metric | Success | Warning | Failure |
|--------|---------|---------|---------|
| count_match | ✅ =  | ⚠️ Diff | ❌ Large Diff |
| total_match | ✅ ≤0.01 | ⚠️ ≤1.0 | ❌ >1.0 |
| duplicates | ✅ 0 | ⚠️ >0 | ❌ Unresolved |
| orphans | ✅ 0 | ⚠️ Linked | ❌ Unlinked |
| unmatched | ✅ 0 | ⚠️ Few | ❌ Many |

---

## 🔧 CONFIGURATION CHECKPOINTS

### Context Flags (Can be enabled/disabled)

```python
# From wizard or config
context = {
    'auto_invoice_created': True/False,      # Auto-invoice new orders
    'create_inventory_picking': True/False,  # Create stock pickings
    'update_inventory_on_sync': True/False,  # Update on amount change
    'update_accounting_on_sync': False,      # Flag for manual review
}
```

### Source: Device Configuration

```python
device.get_reconciliation_config() → {
    'auto_invoice_created': ...,
    'create_inventory_picking': ...,
    'update_inventory_on_sync': ...,
}
```

### Source: Global Settings

```python
ir.config_parameter:
    pos_fiscal.enable_inventory_integration
    pos_fiscal.create_picking_on_create
    pos_fiscal.create_picking_on_sync
    pos_fiscal.auto_invoice_created_orders
```

---

## ⚠️ CRITICAL CHECKPOINTS FOR SUCCESS

### Must Pass (Required)

- ✅ All invoices fetched successfully
- ✅ All orders fetched successfully
- ✅ Device found with matching MRC
- ✅ At least one session exists for date range
- ✅ Invoice map built with no critical errors
- ✅ Order map built with no critical errors
- ✅ Daily report created and updated

### Should Pass (High Priority)

- ⚠️ Order count matches invoice count
- ⚠️ Total amount difference ≤ 0.01
- ⚠️ All duplicates resolved
- ⚠️ All orphans linked or cancelled
- ⚠️ No unreconciled orders remain

### Nice to Have (Optional)

- 📝 All orders have complete partner data
- 📝 All orders have correct payment method
- 📝 All orders have inventory pickings
- 📝 All orders are invoiced

---

## 🐛 COMMON FAILURE POINTS

### 1. No Device Found
```
Error: No POS Device found with MRC: URB0000380
Impact: Entire reconciliation fails
Solution: Verify MRC code, check pos.device records
```

### 2. Format Mismatch
```
Error: FS numbers don't match due to formatting
Example: "00001234" vs "1234" vs 1234
Solution: Implemented standardize_fs_number() with format tolerance
```

### 3. Amount Precision
```
Error: Amount differences (e.g., 0.01 due to rounding)
Impact: Orders appear unmatched
Solution: Tolerance set to 0.01 (one cent)
```

### 4. Missing Session
```
Error: Cannot create order without session
Impact: New order creation fails
Solution: Implemented _find_or_create_session()
```

### 5. Product Not Found
```
Error: Product not found for invoice line
Impact: Order lines creation fails, order created without lines
Solution: Graceful degradation - order created with empty lines
```

### 6. Missing Invoice Lines
```
Error: 'dict' object has no attribute 'line_ids'
Impact: Order creation fails
Solution: Fetch actual invoice record when receiving dict
```

---

## ✅ SUCCESS CRITERIA

### Reconciliation is Successful When:

1. **Count Match:**
   ```
   len(updated_orders) == len(pos_invoices)
   ```

2. **Total Match:**
   ```
   abs(net_order_total - net_zreport_total) <= 0.01
   ```

3. **No Unmatched Invoices:**
   ```
   unmatched_fs_count == 0
   ```

4. **All Duplicates Resolved:**
   ```
   duplicates_found == duplicates_resolved
   ```

5. **No Orphans Remaining:**
   ```
   orphans_linked + orphans_cancelled == orphans_found
   ```

6. **No Unreconciled Orders:**
   ```
   All orders have fiscal_mrc and fs_no
   ```

---

## 📊 DATA VALIDATION RULES

### Invoice (Source of Truth)
- ✅ FS number is unique per device per date
- ✅ Total amount = items total + tax - discounts
- ✅ Payment type must be recognized
- ✅ Date/time must be valid
- ✅ Reference number (if present) is unique

### POS Order (To be Validated)
- ✅ Amount matches corresponding invoice (tolerance: 0.01)
- ✅ FS number matches invoice (with format tolerance)
- ✅ Date matches invoice (tolerance: ±1 day)
- ✅ Payment method matches invoice payment type
- ✅ Lines correspond to invoice items

### Z-Report (Reference Data)
- ✅ Sales total ≥ sum of all sales
- ✅ Refund total ≥ sum of all refunds
- ✅ No older than latest invoice on device
- ✅ Contains full day of sales

---

## 🎯 NEXT STEPS FOR FULL RECONCILIATION

1. **Run reconciliation** via wizard
2. **Review daily report** for count/total match
3. **Check change log** for all modifications
4. **Verify no unmatched invoices** (unmatched_fs_count should be 0)
5. **Compare with Z-Report** for final validation
6. **Handle failures** per common failure points section
7. **Document exceptions** in pos.zreport.exception

---

## 📚 Related Models

| Model | Purpose | Related Records |
|-------|---------|-----------------|
| `pos.order` | POS transaction | Has lines, payments, invoices |
| `pos.invoice` | Fiscal invoice (EJ) | Has lines, reference data |
| `pos.refund` | Refund transaction | Reference to original order |
| `pos.zreport` | Daily closing | Contains daily totals |
| `pos.daily.report` | Reconciliation summary | Audit trail |
| `pos.change.log` | Change audit | Each modification |
| `pos.device` | Fiscal device | Config, MRC mapping |

