# BOM Creation and Manufacturing Workflow

## Overview
This document explains how Bill of Materials (BOM) and Manufacturing Orders (MO) are created for non-standard foam products in the `sales_non_standard` module.

---

## 1. BOM Creation Process

### When BOM is Created
BOM is created when a user clicks **"Calculate and Create Product"** button on a non-standard sale order. This happens in two methods:
- `create_variant_and_save()` - Line 1003
- `create_product_and_add_order_line()` - Line 1080

Both methods call `_create_bom_for_product()` at line 1171.

### BOM Creation Method: `_create_bom_for_product()`

**Location:** `models/model.py`, lines 1171-1369

#### Step 1: Prepare UoM (Unit of Measurement) References
```python
# Gets UoM for different categories:
- Units (for main product)
- m³ (for foam/volume)
- kg (for glue/weight)
- m (for fabric, tape edge, seal/length)
```

#### Step 2: Build BOM Lines (Components)

The method adds components based on what's selected in the sale order:

##### 1. **Foam Component** (Lines 1191-1198)
```python
if self.parent_product:
    bom_lines.append({
        'product_id': self.parent_product.id,
        'product_uom_id': uom_m3.id,  # Volume (m³)
        'product_qty': self.volume,    # Calculated volume
    })
```
- **Product:** Selected parent foam product
- **Quantity:** Volume in m³ (calculated from dimensions)
- **UoM:** Cubic meters (m³)

##### 2. **Glue Component** (Lines 1200-1212)
```python
if self.glue:
    glue_qty = self.glue_qty  # From calculate_glue_quantity()
    bom_lines.append({
        'product_id': glue_product.id,
        'product_uom_id': uom_kg.id,  # Weight (kg)
        'product_qty': glue_qty,       # Formula: 0.75 × (r_length × r_width) in m²
    })
```
- **Product:** "Glue" product (searched by name)
- **Quantity:** Calculated using formula: `0.75 × (Rounded Length in m) × (Rounded Width in m)`
- **UoM:** Kilograms (kg)

##### 3. **Seal Component** (Lines 1214-1231)
```python
if self.Seal and self.seal_type:
    seal_qty = self.seal_qty  # Based on longest dimension
    bom_lines.append({
        'product_id': self.seal_type.id,
        'product_uom_id': seal_product.uom_id.id,  # Uses product's default UoM
        'product_qty': seal_qty,
    })
```
- **Product:** Selected seal type
- **Quantity:** Based on longest dimension (length or width)
- **UoM:** Uses the seal product's default UoM

##### 4. **Tape Edge Component** (Lines 1233-1245)
```python
if self.tape_edge:
    tape_qty = self.tape_edge_qty  # Perimeter-based calculation
    bom_lines.append({
        'product_id': tape_product.id,
        'product_uom_id': uom_meter.id,  # Length (m)
        'product_qty': tape_qty,
    })
```
- **Product:** "Tape Edge" product (searched by name)
- **Quantity:** Perimeter calculation: `((length/100)*2 + (width/100)*2)*2`
- **UoM:** Meters (m)

##### 5. **Fabric Components** (Lines 1247-1262)
```python
# Fabric 1 (H-Fabric)
if self.fabric and self.fabric_1:
    bom_lines.append({
        'product_id': self.fabric_1.id,
        'product_uom_id': uom_meter.id,
        'product_qty': self.fabric_size_1,  # ((width + 4)/100) * 2
    })

# Fabric 2 (Fasha)
if self.fabric and self.fabric_2:
    bom_lines.append({
        'product_id': self.fabric_2.id,
        'product_uom_id': uom_meter.id,
        'product_qty': self.fabric_size_2,  # Perimeter + corner adjustment
    })
```
- **Fabric 1:** Horizontal fabric, quantity based on width
- **Fabric 2:** Fasha (edge fabric), quantity based on perimeter
- **UoM:** Meters (m)

#### Step 3: UoM Validation (Lines 1264-1277)
```python
# Ensures each component uses its default UoM
for line_vals in bom_lines:
    component = self.env['product.product'].browse(line_vals['product_id'])
    # Override with component's default UoM if different
    line_vals['product_uom_id'] = component.uom_id.id
```
This ensures UoM compatibility and prevents category mismatches.

#### Step 4: Create BOM Record (Lines 1279-1369)
```python
bom_vals = {
    'product_tmpl_id': product_obj.product_tmpl_id.id,
    'product_id': product_obj.id,
    'type': 'normal',
    'product_qty': 1.0,  # 1 unit of finished product
    'product_uom_id': uom_unit.id,
    'bom_line_ids': bom_lines,  # All components
    'company_id': self.company_id.id,
    'picking_type_id': picking_type.id,  # From sale order
}

self.env['mrp.bom'].create(bom_vals)
```

**Key Points:**
- BOM is for 1 unit of finished product
- Includes all selected components with calculated quantities
- Uses picking type from sale order (based on manufacturing site)
- Extensive logging for debugging

---

## 2. Manufacturing Order Creation Process

### When MO is Created
Manufacturing Order is created when a **non-standard sale order is confirmed** (clicking "Confirm" button).

**Location:** `models/model.py`, `action_confirm()` method, lines 515-635

### Step-by-Step MO Creation

#### Step 1: Validate Order (Lines 522-531)
```python
# Ensure all order lines have correct UoM
for line in self.order_line:
    if line.product_uom != line.product_id.uom_id:
        line.product_uom = line.product_id.uom_id

# Skip if not non-standard order
if not self.non_standard:
    return super().action_confirm()
```

#### Step 2: Confirm Sale Order (Line 536)
```python
# Confirm order first (without creating MOs automatically)
res = super(ExtendSale, self.with_context(bypass_mo_creation=True)).action_confirm()
```

#### Step 3: Find Main Product (Lines 538-558)
```python
# Find main product (storable product with BOM)
for line in self.order_line:
    if line.product_id.detailed_type == 'product':
        main_product = line.product_id
        break

# If not found, use first product
if not main_product:
    main_product = self.order_line[0].product_id
```

#### Step 4: Find or Create BOM (Lines 561-577)
```python
# Try to find existing BOM
bom = self.env['mrp.bom']._bom_find(
    main_product,
    company_id=self.company_id.id,
    bom_type='normal'
).get(main_product, self.env['mrp.bom'])

# Create simple BOM if none exists
if not bom:
    bom = self.env['mrp.bom'].create({
        'product_tmpl_id': main_product.product_tmpl_id.id,
        'product_qty': 1,
        'product_uom_id': main_product.uom_id.id,
        'type': 'normal',
        'company_id': self.company_id.id,
    })
```

#### Step 5: Create Manufacturing Order (Lines 581-597)
```python
mo_vals = {
    'product_id': main_product.id,
    'product_qty': main_product_line.product_uom_qty,
    'product_uom_id': main_product.uom_id.id,
    'bom_id': bom.id,  # Link to BOM
    'origin': self.name,  # Sale order name
    'company_id': self.company_id.id,
    'date_planned_start': fields.Datetime.now(),
    'sale_order_id': self.id,
    'sale_line_id': main_product_line.id,
    'isNOnStandard': True,  # Flag for non-standard orders
}

mo = self.env['mrp.production'].create(mo_vals)
```

**MO Naming:** Custom naming handled in `models/products.py` (ExtendMrp.create())
- Prefix: `BAZAR/MO/`
- Auto-generated sequence number

#### Step 6: Add Components as Raw Materials (Lines 599-616)
```python
# Add all other order line products as raw materials
for line in self.order_line:
    if line.product_id != main_product:
        self.env['stock.move'].create({
            'production_id': mo.id,
            'product_id': line.product_id.id,
            'product_uom_qty': line.product_uom_qty,
            'product_uom': line.product_uom.id,
            'name': line.name or line.product_id.name,
            'location_id': mo.location_src_id.id,
            'location_dest_id': mo.product_id.property_stock_production.id,
            'raw_material_production_id': mo.id,
            'state': 'draft',
        })
```

**Important:** This creates `stock.move` records directly, not BOM lines. These are raw material moves for the MO.

#### Step 7: Confirm Manufacturing Order (Line 621)
```python
mo.action_confirm()
```

This:
- Validates the MO
- Creates stock moves from BOM
- Sets MO to 'confirmed' state

#### Step 8: Link Moves to Order Lines (Lines 623-627)
```python
# Update order lines with MO's moves
if mo.move_raw_ids:
    move_ids = mo.move_raw_ids.ids
    for line in self.order_line:
        line.write({'move_ids': [(6, 0, move_ids)]})
```

---

## 3. Component Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User Creates Non-Standard Sale Order                    │
│    - Enters dimensions (length, width, height)              │
│    - Selects foam type, fabric, glue, seal, etc.           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. User Clicks "Calculate and Create Product"              │
│    → Calls calculate_and_save()                            │
│    → Calls create_product_and_add_order_line()             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Product Created                                          │
│    - Product name: "Shape ParentProduct LxWxH"             │
│    - Routes: MTO + Manufacture                              │
│    - Type: Storable (product)                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. BOM Created (_create_bom_for_product)                    │
│    ├─ Foam: volume (m³)                                     │
│    ├─ Glue: 0.75 × (r_length × r_width) in m² (kg)        │
│    ├─ Seal: longest dimension (m)                           │
│    ├─ Tape Edge: perimeter × 2 (m)                          │
│    └─ Fabric: calculated sizes (m)                          │
│                                                              │
│    BOM Structure:                                            │
│    ┌──────────────────────────────────────┐                │
│    │ Finished Product (1 unit)            │                │
│    ├──────────────────────────────────────┤                │
│    │ - Foam: X m³                         │                │
│    │ - Glue: Y kg                         │                │
│    │ - Seal: Z m                          │                │
│    │ - Tape Edge: W m                     │                │
│    │ - Fabric 1: V m                      │                │
│    │ - Fabric 2: U m                      │                │
│    └──────────────────────────────────────┘                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Product Added to Sale Order Line                         │
│    - Price: final_total_all (calculated total)             │
│    - Quantity: 1                                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. User Confirms Sale Order                                 │
│    → Calls action_confirm()                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Manufacturing Order Created                             │
│    - Product: Main product from order line                  │
│    - BOM: Linked BOM (created in step 4)                    │
│    - Origin: Sale order name                                │
│    - Name: BAZAR/MO/XXXXX (auto-generated)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. Components Added as Raw Material Moves                   │
│    - All other order line products become raw materials     │
│    - Created as stock.move records                          │
│    - Linked to MO                                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. MO Confirmed                                             │
│    - MO state: 'confirmed'                                  │
│    - Stock moves created from BOM                           │
│    - Ready for production                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Key Relationships

### BOM Structure
```
mrp.bom
├─ product_tmpl_id → product.template (finished product)
├─ product_id → product.product (finished product variant)
├─ product_qty → 1.0 (quantity of finished product)
├─ product_uom_id → uom.uom (UoM for finished product)
├─ picking_type_id → stock.picking.type (manufacturing site)
└─ bom_line_ids → mrp.bom.line[]
    ├─ product_id → product.product (component)
    ├─ product_qty → float (quantity needed)
    └─ product_uom_id → uom.uom (component UoM)
```

### Manufacturing Order Structure
```
mrp.production
├─ product_id → product.product (what to produce)
├─ product_qty → float (how many to produce)
├─ bom_id → mrp.bom (which BOM to use)
├─ origin → sale.order.name (source sale order)
├─ sale_order_id → sale.order (linked sale order)
├─ isNOnStandard → boolean (flag for non-standard)
├─ manufacturing_site → selection (from sale order)
└─ move_raw_ids → stock.move[] (raw material moves from BOM)
```

### Component Flow
```
Sale Order Line Products
    ↓
BOM Lines (when BOM created)
    ↓
Manufacturing Order (when SO confirmed)
    ↓
Stock Moves (raw materials)
    ↓
Production Process
```

---

## 5. Important Notes

### BOM vs Direct Components
- **BOM Components:** Created when product is created (via `_create_bom_for_product`)
  - These are the "recipe" for manufacturing
  - Used by Odoo's standard manufacturing process
  
- **Direct Raw Material Moves:** Created in `action_confirm()` for additional components
  - These are added directly as `stock.move` records
  - Used for products that aren't in the BOM but are needed

### UoM Handling
- The system validates and corrects UoM categories
- Each component uses its default UoM
- Prevents category mismatches (e.g., Volume vs Weight)

### Manufacturing Site
- Selected in sale order (`manufacturing_site` field)
- Automatically selects `picking_type_id` based on site
- Picking type is used in BOM creation
- Transferred to MO when created

### Sequence Generation
- MO names: `BAZAR/MO/XXXXX`
- Custom sequence generation in `ExtendMrp._get_next_serial_number()`
- Fallback mechanisms if sequence fails

---

## 6. Code Locations Summary

| Functionality | File | Method | Lines |
|--------------|------|--------|-------|
| BOM Creation | `models/model.py` | `_create_bom_for_product()` | 1171-1369 |
| MO Creation | `models/model.py` | `action_confirm()` | 515-635 |
| MO Naming | `models/products.py` | `ExtendMrp.create()` | 145-243 |
| Component Addition | `models/model.py` | `action_confirm()` | 599-616 |
| Glue Calculation | `models/model.py` | `calculate_glue_quantity()` | 1542-1573 |

---

## 7. Testing Checklist

When testing BOM and MO creation:

1. ✅ Create non-standard sale order
2. ✅ Enter dimensions and select components
3. ✅ Click "Calculate and Create Product"
4. ✅ Verify BOM created with correct components
5. ✅ Verify component quantities match calculations
6. ✅ Verify UoM for each component
7. ✅ Confirm sale order
8. ✅ Verify MO created with correct BOM
9. ✅ Verify MO has raw material moves
10. ✅ Verify MO can be confirmed and produced

---

## 8. Troubleshooting

### BOM Not Created
- Check if `_create_bom_for_product()` is called
- Verify `bom_lines` list is not empty
- Check logs for UoM errors

### MO Not Created
- Verify `non_standard` flag is True
- Check if main product is found
- Verify BOM exists for main product

### Components Missing
- Check if components are selected in sale order
- Verify component products exist in system
- Check UoM compatibility

### UoM Errors
- Verify component UoM categories match
- Check if default UoM is set for components
- Review UoM validation logs

