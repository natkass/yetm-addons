# Stock Valuation Report

## Overview

This module allows you to generate stock valuation reports as of a specific date. It provides accurate inventory quantities and values per product per location, with support for:

- **Date-based snapshots**: View inventory as of any historical date
- **Average cost calculation**: Includes landed costs in valuation
- **UoM-aware conversions**: All quantities converted to product base UoM
- **Internal locations only**: Excludes customer/vendor/transit locations
- **Excel export**: Download results in formatted Excel file
- **Product filtering**: Optional filter by product code or name

## Features

### Dual-Dating Logic for Valuation

- **Regular SVLs**: Uses `create_date` for filtering
- **Landed-cost SVLs**: Uses `account_move.date` (when qty=0 but value≠0)
- Ensures accurate cost accounting for all scenarios

### Average Cost Calculation

Formula: `(total_value + landed_costs) / total_quantity`

### Robust UoM Conversion

- Handles "bigger", "smaller", and "reference" UoM types
- Category-aware conversions
- Rounding precision applied

## Installation

1. **Install Python dependency**:
   ```bash
   pip install xlsxwriter
   ```

2. **Copy module** to your Odoo addons directory

3. **Update Apps List**:
   - Go to Apps menu
   - Click "Update Apps List"

4. **Install module**:
   - Search for "Stock Valuation Report"
   - Click Install

## Usage

1. Navigate to: **Inventory → Stock Valuation Report → Generate Valuation Report**

2. Fill in the wizard:
   - **End Date**: The date for the snapshot (required)
   - **Product Filter**: Optional - filter by product code or name
   - **Debug UoM Conversions**: Enable to see conversion logs (for troubleshooting)

3. Click **Generate Snapshot**

4. Download the Excel file when ready

## Excel Output

The generated Excel file contains:

| Column | Description |
|--------|-------------|
| Product Code | Product internal reference |
| Product Name | Product display name |
| Quantity | Stock quantity in base UoM |
| Amount | Value (quantity × average cost) |
| UoM | Product unit of measure |
| Location | Stock location path |

## Technical Details

### Models

- `stock.snapshot.wizard`: TransientModel for wizard interface

### Dependencies

- `stock`: Core inventory module
- `stock_account`: Inventory valuation/accounting
- Python library: `xlsxwriter`

### Key Methods

- `_compute_average_costs()`: Calculate average costs from SVLs
- `_compute_quantities()`: Calculate quantities from move lines
- `_convert_qty()`: UoM conversion logic
- `_generate_excel()`: Excel file generation

## Use Cases

- **Period-end valuations**: Generate report at month/year end
- **Inventory audits**: Compare system vs physical inventory
- **Historical analysis**: View inventory at any past date
- **Reconciliation**: Verify valuation calculations

## Security

Access granted to:
- Stock User (`stock.group_stock_user`)
- Stock Manager (`stock.group_stock_manager`)

## Credits

Converted from standalone Python script to Odoo module.

## License

LGPL-3
