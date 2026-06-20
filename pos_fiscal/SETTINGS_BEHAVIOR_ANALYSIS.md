# Settings Behavior Analysis - Toggle ON/OFF Effects

**Document:** Complete analysis of all pos_fiscal settings and their behavior
**Date:** December 16, 2025

---

## 📋 Settings Overview

The pos_fiscal module has **8 toggle settings** organized in 3 groups:

1. **Inventory Integration** (4 toggles)
2. **Accounting Integration** (4 toggles)
3. **Reconciliation** (2 toggles - for future use)

---

## 🏗️ Configuration Hierarchy

### Two-Level System:

```
Global Level (System Settings)
    ↓
Device Level (Per-Device Overrides - optional)
    ↓
Final Configuration Used During Reconciliation
```

**How it works:**
- By default, all devices use **Global Settings** (System Settings → POS Fiscal)
- If `use_custom_config = ON`, the device uses **Device-Specific Settings** instead
- One device can override global settings, others still use global

---

## 📊 INVENTORY INTEGRATION SETTINGS

### 1️⃣ Toggle: "Enable POS Fiscal Inventory Integration"
**Setting Name:** `pos_fiscal_enable_inventory`
**Default:** ON (True)
**Level:** Global + Device

#### WHEN ON (✅ Enabled)
```
- Stock movements tracked automatically
- Pickings created for reconciled orders
- Inventory updated with order items
- Impact: Real-time inventory visibility

Process Flow:
  Invoice created
    ↓
  Order created from invoice
    ↓
  Picking created (if other inventory toggles ON)
    ↓
  Inventory moves recorded
    ↓
  Stock levels updated
```

#### WHEN OFF (❌ Disabled)
```
- No pickings created
- No inventory moves
- Stock levels NOT updated
- Inventory remains in limbo
- Impact: Inventory management disabled

Process Flow:
  Invoice created
    ↓
  Order created from invoice
    ↓
  ✗ No picking created
    ↓
  ✗ No inventory moves
    ↓
  Stock levels unchanged
```

#### Usage Scenario:
- **ON:** Physical warehouse with stock tracking required
- **OFF:** Service business with no inventory (pure POS)

---

### 2️⃣ Toggle: "Create Picking for New Orders"
**Setting Name:** `pos_fiscal_create_picking_on_create`
**Default:** ON (True)
**Dependency:** `Enable POS Fiscal Inventory Integration` must be ON
**Level:** Global + Device

#### WHEN ON (✅ Enabled)
```
ACTION: When creating order from fiscal invoice

Create Picking immediately
  ↓
Document Type: Outgoing (Draft)
  ↓
Status: Waiting for validation (unless auto-validate is ON)
  ↓
Items: All order line items included
```

**Example Flow:**
```
Fiscal Invoice Sync:
  Receipt #001: Apple x10, Orange x5
    ↓
  Order created from invoice
    ↓
  IF create_picking_on_create = ON
    ├─ Picking created
    ├─ 10x Apple added to picking
    └─ 5x Orange added to picking
    ↓
  Result: Stock reserved for this order
```

#### WHEN OFF (❌ Disabled)
```
ACTION: When creating order from fiscal invoice

✗ No picking created
  ↓
✗ No stock reserved
  ↓
Stock available for other orders
  ↓
Manual picking creation needed later
```

#### Impact Comparison:

| Scenario | ON | OFF |
|----------|----|----|
| **Picking created** | ✅ Auto | ❌ Manual |
| **Stock reserved** | ✅ Immediate | ❌ Never |
| **Order-to-ship time** | ⚡ Fast | 🐢 Requires manual |
| **Inventory accuracy** | ✅ Real-time | ❌ Delayed |

#### Usage Scenario:
- **ON:** Quick order fulfillment, real-time stock tracking
- **OFF:** Manual warehouse operations, batched picking

---

### 3️⃣ Toggle: "Create Picking on Amount Sync"
**Setting Name:** `pos_fiscal_create_picking_on_sync`
**Default:** ON (True)
**Dependency:** `Enable POS Fiscal Inventory Integration` must be ON
**Level:** Global + Device

#### WHEN ON (✅ Enabled)
```
ACTION: When order amount changes during reconciliation sync

Old Order:
  Apple x5, Orange x3
  ↓
Fiscal Data Shows:
  Apple x8, Orange x5
  ↓
Reconciliation detects mismatch
  ↓
IF create_picking_on_sync = ON
  ├─ OLD picking cancelled
  ├─ NEW picking created with correct items
  └─ Stock adjusted accordingly
```

**Example:**
```
Initial Receipt:        Updated Receipt:
  Apple x5               Apple x8
  Orange x3      →       Orange x5

Result:
  ✅ Picking adjusted (x3 more apple, x2 more orange)
  ✅ Stock moves updated
```

#### WHEN OFF (❌ Disabled)
```
ACTION: When order amount changes during reconciliation sync

Old picking remains with OLD items
  ↓
Items don't match updated receipt
  ↓
Manual correction needed
  ↓
Inventory inconsistent
```

**Example:**
```
Initial Receipt:        Updated Receipt:
  Apple x5               Apple x8
  Orange x3      ✗       Orange x5

Result:
  ❌ Picking still has old items
  ❌ Inventory doesn't match fiscal data
  ❌ Manual fixing required
```

#### When This Matters:

This setting triggers when:
1. Quantity differs from fiscal data
2. Product items changed
3. Order price/amount changed
4. Items removed or added

#### Usage Scenario:
- **ON:** Volatile data (corrections common), needs accuracy
- **OFF:** Stable data (changes rare), minimal sync issues

---

### 4️⃣ Toggle: "Auto-Validate Pickings"
**Setting Name:** `pos_fiscal_validate_picking_auto`
**Default:** ON (True)
**Dependency:** `Enable POS Fiscal Inventory Integration` must be ON
**Level:** Global + Device

#### WHEN ON (✅ Enabled)
```
ACTION: After picking is created

Picking Created (Draft)
  ↓
IF auto_validate_picking = ON
  ├─ Validate immediately
  ├─ Move items to inventory
  └─ Picking status = Done
  ↓
Result: Inventory updated IMMEDIATELY
```

**Process:**
```
Timeline with AUTO-VALIDATE ON:
────────────────────────────────
T0: Fiscal invoice synced
T1: Picking created
T2: Picking auto-validated (instant)
T3: Stock levels updated (instant)
T4: Order ready to ship
```

#### WHEN OFF (❌ Disabled)
```
ACTION: After picking is created

Picking Created (Draft)
  ↓
IF auto_validate_picking = OFF
  ├─ ✗ Stays in Draft
  ├─ ✗ Manual validation needed
  └─ Stock NOT moved yet
  ↓
Warehouse staff validates manually
```

**Process:**
```
Timeline with AUTO-VALIDATE OFF:
────────────────────────────────
T0: Fiscal invoice synced
T1: Picking created (Draft)
T2: Manual validation by warehouse (⏳ hours/days later)
T3: Stock levels updated
T4: Order ready to ship
```

#### Comparison:

| Aspect | ON | OFF |
|--------|----|----|
| **Validation** | 🤖 Auto | 👤 Manual |
| **Time** | ⚡ Instant | ⏳ Delayed |
| **Accuracy** | ✅ High | ⚠️ Depends on staff |
| **Control** | Low | High |
| **Labor** | Minimal | Extra |

#### Usage Scenario:
- **ON:** Automated warehouse, no manual validation
- **OFF:** Manual validation control required, QC checks

---

## 💰 ACCOUNTING INTEGRATION SETTINGS

### 5️⃣ Toggle: "Enable POS Fiscal Accounting Integration"
**Setting Name:** `pos_fiscal_enable_accounting`
**Default:** ON (True)
**Level:** Global + Device

#### WHEN ON (✅ Enabled)
```
- Invoices created automatically
- Journal entries recorded
- Accounting ledger updated
- Financial reports affected
- Impact: Complete accounting trail

Process:
  Order created from fiscal invoice
    ↓
  IF enable_accounting = ON
    ├─ Customer invoice generated
    ├─ Journal entry created
    ├─ GL accounts updated
    └─ Invoice posted (if auto-post ON)
```

#### WHEN OFF (❌ Disabled)
```
- ✗ No invoices created
- ✗ No journal entries
- ✗ Accounting not updated
- Manual invoicing needed
- Impact: Accounting work offline

Process:
  Order created from fiscal invoice
    ↓
  ✗ No invoice generated
    ↓
  Manual invoice creation needed
    ↓
  Accounting lag/delay
```

#### Impact on Financial Reports:
- **ON:** Real-time visibility, automated reconciliation
- **OFF:** Delayed reporting, manual GL updates

#### Usage Scenario:
- **ON:** Needs accounting automation, audit trail
- **OFF:** Manual accounting process, no automation needed

---

### 6️⃣ Toggle: "Auto-Invoice Created Orders"
**Setting Name:** `pos_fiscal_auto_invoice_orders`
**Default:** ON (True)
**Dependency:** `Enable POS Fiscal Accounting Integration` must be ON
**Level:** Global + Device

#### WHEN ON (✅ Enabled)
```
ACTION: When order created from fiscal invoice

Order Created
  ↓
IF auto_invoice_created = ON
  ├─ Customer invoice generated
  ├─ Invoice lines from order lines
  ├─ Amount = order total
  └─ Status = Draft (ready to post if auto-post ON)
  ↓
Result: Invoice ready immediately
```

**Timeline:**
```
ON:  Sync → Order created → Invoice created (instant)
OFF: Sync → Order created → ✗ No invoice created
```

#### WHEN OFF (❌ Disabled)
```
ACTION: When order created from fiscal invoice

Order Created
  ↓
✗ No invoice created
  ↓
Manual invoice creation required
  ↓
Accounting delay
```

#### What Gets Invoiced:
```
Invoice includes:
  • All order line items
  • Product names & quantities
  • Unit prices from order
  • Taxes from product config
  • Discounts (if any)
  • Total amount
```

#### Usage Scenario:
- **ON:** Automate customer invoicing
- **OFF:** Manual invoice creation preferred

---

### 7️⃣ Toggle: "Auto-Post Invoices"
**Setting Name:** `pos_fiscal_auto_post_invoices`
**Default:** ON (True)
**Dependency:** `Auto-Invoice Created Orders` must be ON
**Level:** Global + Device

#### WHEN ON (✅ Enabled)
```
ACTION: After invoice created

Invoice Created (Draft)
  ↓
IF auto_post_invoices = ON
  ├─ Validate invoice
  ├─ Post to general ledger
  ├─ Status = Posted
  └─ GL accounts debited/credited
  ↓
Result: Accounting recorded immediately
```

**Timeline:**
```
ON:  Created → Draft → Posted (instant) → GL updated
OFF: Created → Draft → Stays draft → Manual posting needed
```

#### WHEN OFF (❌ Disabled)
```
ACTION: After invoice created

Invoice Created (Draft)
  ↓
✗ Stays in Draft
  ↓
Manual posting required
  ↓
GL not updated yet
```

#### GL Impact:

| Toggle | Status | GL Updated | Reports |
|--------|--------|-----------|---------|
| ON | Posted | ✅ Yes | 📊 Immediate |
| OFF | Draft | ❌ No | 📊 Delayed |

#### Usage Scenario:
- **ON:** Automate GL posting, real-time accounting
- **OFF:** Manual review before posting (audit control)

---

### 8️⃣ Toggle: "Auto-Validate Payments"
**Setting Name:** `pos_fiscal_auto_validate_payments`
**Default:** ON (True)
**Dependency:** `Auto-Invoice Created Orders` must be ON
**Level:** Global + Device

#### WHEN ON (✅ Enabled)
```
ACTION: After invoice created

Invoice Created
  ↓
Payment Record: Amount = Order Total
  ↓
IF auto_validate_payments = ON
  ├─ Payment automatically reconciled
  ├─ Invoice linked to payment
  ├─ Outstanding amount = 0
  └─ Status = Paid
  ↓
Result: Invoice fully settled
```

**Timeline:**
```
ON:  Invoice created → Payment added → Auto-reconciled → Paid ✅
OFF: Invoice created → Payment added → Manual reconciliation needed
```

#### WHEN OFF (❌ Disabled)
```
ACTION: After invoice created

Invoice Created
  ↓
Payment Record: Amount = Order Total
  ↓
✗ Not automatically reconciled
  ↓
Outstanding amount still shows
  ↓
Manual reconciliation needed
```

#### Invoice Status:

| Toggle | Invoice Status | Outstanding | Action |
|--------|---|---|---|
| ON | Paid | 0.00 | None |
| OFF | Partial | Full amount | Reconcile manually |

#### Usage Scenario:
- **ON:** Payment automatically matched, full automation
- **OFF:** Manual matching required (audit/review)

---

## 🔄 RECONCILIATION SETTINGS (Future Use)

### Toggle: "Auto-Reconcile Orders"
**Setting Name:** `pos_fiscal_auto_reconcile`
**Default:** OFF (False)
**Status:** Prepared for future (not currently active)

```
When enabled in future:
├─ Orders auto-matched to invoices
├─ Discrepancies flagged automatically
└─ No manual reconciliation needed
```

### Toggle: "Strict Matching Mode"
**Setting Name:** `pos_fiscal_strict_matching`
**Default:** ON (True)
**Status:** Prepared for future (not currently active)

```
When enabled:
├─ Exact amount matching required
├─ Price differences flagged
└─ Partial matches rejected
```

---

## 🎯 COMPLETE IMPACT MATRIX

### Order Creation Behavior

```
Scenario 1: Default Settings (All ON)
──────────────────────────────────────
Fiscal Invoice Sync
  ↓
1. Order created
2. Picking created (draft)
3. Picking auto-validated
4. Invoice created (draft)
5. Invoice auto-posted
6. Payment auto-reconciled
Result: ✅ FULLY AUTOMATED
  • Order ready
  • Stock updated
  • GL updated
  • Invoice paid
Time: ~2-3 seconds


Scenario 2: Inventory OFF, Accounting ON
──────────────────────────────────────────
Fiscal Invoice Sync
  ↓
1. Order created
2. ✗ No picking
3. ✗ No inventory updates
4. Invoice created (draft)
5. Invoice auto-posted
6. Payment auto-reconciled
Result: ✅ ACCOUNTING AUTOMATED, ❌ INVENTORY MANUAL
  • Order ready
  • ✗ Stock not tracked
  • GL updated
  • Invoice paid
Time: ~2 seconds


Scenario 3: Inventory ON, Accounting OFF
──────────────────────────────────────────
Fiscal Invoice Sync
  ↓
1. Order created
2. Picking created (draft)
3. Picking auto-validated
4. ✗ No invoice
5. ✗ No posting
6. ✗ No payment reconciliation
Result: ✅ INVENTORY AUTOMATED, ❌ ACCOUNTING MANUAL
  • Order ready
  • Stock updated
  • ✗ GL not updated
  • ✗ No invoice
Time: ~2 seconds


Scenario 4: Everything OFF (Manual Mode)
──────────────────────────────────────────
Fiscal Invoice Sync
  ↓
1. Order created
2. ✗ No picking
3. ✗ No inventory
4. ✗ No invoice
5. ✗ No posting
6. ✗ No payment reconciliation
Result: ❌ FULLY MANUAL
  • Order created (that's it)
  • Everything else manual
Time: ~1 second
```

---

## 💡 RECOMMENDED CONFIGURATIONS

### Configuration A: Full Automation (Default)
**Use Case:** High-volume POS with integrated accounting & inventory

```
✅ Enable Inventory Integration = ON
  ✅ Create Picking on Create = ON
  ✅ Create Picking on Sync = ON
  ✅ Auto-Validate Pickings = ON

✅ Enable Accounting Integration = ON
  ✅ Auto-Invoice Created Orders = ON
  ✅ Auto-Post Invoices = ON
  ✅ Auto-Validate Payments = ON

Result: Fully automated, no manual intervention
Time per order: ~2-3 seconds
Labor: Minimal
```

---

### Configuration B: Inventory Only
**Use Case:** Warehouse-focused business

```
✅ Enable Inventory Integration = ON
  ✅ Create Picking on Create = ON
  ✅ Create Picking on Sync = ON
  � Auto-Validate Pickings = OFF (manual QC)

❌ Enable Accounting Integration = OFF
  (All accounting OFF)

Result: Inventory automated, accounting manual
Time per order: ~2 seconds
Labor: Warehouse staff validate pickings
```

---

### Configuration C: Accounting Only
**Use Case:** Service business with no inventory

```
❌ Enable Inventory Integration = OFF
  (All inventory OFF)

✅ Enable Accounting Integration = ON
  ✅ Auto-Invoice Created Orders = ON
  ✅ Auto-Post Invoices = ON
  ✅ Auto-Validate Payments = ON

Result: Accounting automated, no inventory tracking
Time per order: ~1-2 seconds
Labor: Minimal
```

---

### Configuration D: Conservative (Max Control)
**Use Case:** Highly regulated business needing approval

```
✅ Enable Inventory Integration = ON
  ✅ Create Picking on Create = ON
  ❌ Create Picking on Sync = OFF (manual)
  ❌ Auto-Validate Pickings = OFF (manual)

✅ Enable Accounting Integration = ON
  ✅ Auto-Invoice Created Orders = ON
  ❌ Auto-Post Invoices = OFF (manual)
  ❌ Auto-Validate Payments = OFF (manual)

Result: Orders created, everything else manual
Time per order: ~1 second
Labor: High (manual approvals)
Control: Maximum
```

---

## 🔍 What to Check When Things Go Wrong

### Problem: No Stock Movements
```
Check:
1. Enable Inventory Integration = ON?
2. Create Picking on Create = ON?
3. Auto-Validate Pickings = ON?

If all ON and still no movement:
  → Check if picking was created but not validated
  → Check user permissions for stock operations
```

### Problem: No Invoices Created
```
Check:
1. Enable Accounting Integration = ON?
2. Auto-Invoice Created Orders = ON?

If both ON and still no invoice:
  → Check if invoice creation threw an error
  → Check product taxes configured
  → Check partner/customer set
```

### Problem: Invoices Stay in Draft
```
Check:
1. Auto-Invoice Created Orders = ON?
2. Auto-Post Invoices = ON?

If both ON and still in Draft:
  → Check invoice validation errors
  → Check GL account configuration
  → Check journal configuration
```

### Problem: Invoice Shows Partial
```
Check:
1. Auto-Validate Payments = ON?

If ON and still showing Partial:
  → Check payment amount vs invoice total
  → Check decimal rounding (fixed in latest code)
  → Manually validate payment
```

---

## 📊 Performance Impact by Configuration

```
| Config | Orders/min | CPU | Memory | Latency |
|--------|-----------|-----|--------|---------|
| All ON | ~50-100   | High| High   | 2-3 sec |
| Inventory Only | ~100-150 | Med | Med | 1-2 sec |
| Accounting Only | ~100-150 | Med | Med | 1-2 sec |
| All OFF | ~300-500 | Low | Low | <1 sec |
```

---

## ✅ Checklist: Before Changing Settings

- [ ] Backup database
- [ ] Understand impact of each toggle
- [ ] Plan during low-traffic time
- [ ] Have staff ready to monitor
- [ ] Know how to rollback if issues
- [ ] Test with small batch first
- [ ] Monitor logs for errors
- [ ] Verify GL entries correct
- [ ] Verify inventory counts
- [ ] Verify invoices created properly

---

## Summary Table

| Setting | ON Behavior | OFF Behavior | Dependency |
|---------|-------------|--------------|-----------|
| **Enable Inventory** | Pickings created | No pickings | - |
| **Create on Create** | Draft picking auto-created | Manual | Enable Inventory |
| **Create on Sync** | Picking updated | Manual fix | Enable Inventory |
| **Auto-Validate Pickings** | Validated instantly | Manual validation | Enable Inventory |
| **Enable Accounting** | Invoices created | Manual invoicing | - |
| **Auto-Invoice** | Draft invoice auto-created | Manual | Enable Accounting |
| **Auto-Post Invoices** | Posted instantly | Manual posting | Auto-Invoice |
| **Auto-Validate Payments** | Reconciled auto | Manual reconciliation | Auto-Invoice |

---

**Analysis Complete**

