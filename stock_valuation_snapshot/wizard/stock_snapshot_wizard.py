# -*- coding: utf-8 -*-
"""
Stock Valuation Snapshot Wizard - Odoo 17
Generates stock valuation report as of a specific date with Excel export
"""

import base64
from io import BytesIO
from collections import defaultdict
from typing import Dict, Tuple

from odoo import models, fields, api, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class StockSnapshotWizard(models.TransientModel):
    _name = 'stock.snapshot.wizard'
    _description = 'Stock Valuation Snapshot Wizard'

    start_date = fields.Date(
        string='Start Date',
        required=False,
        help='Optional: Filter stock movements from this date. Leave empty for all historical data.'
    )
    end_date = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.context_today,
        help='Stock snapshot will be calculated as of this date'
    )
    product_filter = fields.Char(
        string='Product Filter',
        help='Optional filter by product code or name'
    )
    product_ids = fields.Many2many(
        'product.product',
        'stock_snapshot_wizard_product_rel',
        'wizard_id',
        'product_id',
        string='Products',
        domain=[('type', '=', 'product')],
        help='Filter by specific products. Leave empty for all products.'
    )
    location_ids = fields.Many2many(
        'stock.location',
        'stock_snapshot_wizard_location_rel',
        'wizard_id',
        'location_id',
        string='Locations',
        domain=[('usage', '=', 'internal')],
        help='Filter by specific locations. Leave empty for all internal locations.'
    )
    debug_conversions = fields.Boolean(
        string='Debug UoM Conversions',
        default=False,
        help='Log UoM conversion details'
    )
    file_data = fields.Binary(
        string='Excel File',
        readonly=True,
        attachment=False
    )
    file_name = fields.Char(
        string='File Name',
        readonly=True
    )
    snapshot_line_ids = fields.One2many(
        'stock.snapshot.line',
        'wizard_id',
        string='Snapshot Lines'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('view', 'View'),
        ('excel', 'Excel')
    ], default='draft')

    def _multiplier_to_reference(self, uom):
        """Calculate multiplier to convert to reference UoM."""
        if not uom:
            return 1.0

        factor = float(uom.factor or 1.0)
        uom_type = (uom.uom_type or 'reference').lower()

        if uom_type == 'reference':
            return 1.0
        if factor <= 0:
            return 1.0

        m1 = factor
        m2 = 1.0 / factor

        if uom_type == 'bigger':
            return m1 if m1 > 1.0 else m2
        if uom_type == 'smaller':
            return m1 if m1 < 1.0 else m2

        return factor

    def _convert_qty(self, qty, from_uom, to_uom):
        """Convert quantity from one UoM to another."""
        if qty == 0 or not from_uom or not to_uom:
            return qty

        if from_uom.category_id != to_uom.category_id:
            return qty

        m_from = self._multiplier_to_reference(from_uom)
        m_to = self._multiplier_to_reference(to_uom)

        if m_from <= 0 or m_to <= 0:
            return qty

        converted = qty * (m_from / m_to)

        rounding = float(to_uom.rounding or 0.0)
        if rounding > 0:
            converted = round(converted / rounding) * rounding

        return converted

    def _compute_average_costs(self, end_date_str, product_ids=None):
        """Compute average cost per product from SVLs with fallback to standard_price.

        Returns average cost WITHOUT landed cost (landed cost is tracked separately).
        """
        SVL = self.env['stock.valuation.layer']

        # First, fetch regular stock movements (qty != 0) up to end_date
        regular_svl_domain = [
            ('product_id.active', '=', True),
            ('quantity', '!=', 0),  # Regular movements have qty
            '|',
            ('account_move_id.date', '<=', end_date_str),
            ('create_date', '<=', end_date_str + ' 23:59:59'),
        ]
        regular_svls = SVL.search(regular_svl_domain)

        product_tot_qty = defaultdict(float)
        product_tot_val = defaultdict(float)
        prod_ids_from_svl = set()

        for svl in regular_svls:
            pid = svl.product_id.id
            if not pid:
                continue

            qty = float(svl.quantity or 0.0)
            val = float(svl.value or 0.0)

            if svl.account_move_id and svl.account_move_id.date:
                effective_date = fields.Date.to_string(svl.account_move_id.date)
            else:
                effective_date = fields.Datetime.to_string(svl.create_date)[:10]

            if effective_date and effective_date > end_date_str:
                continue

            product_tot_qty[pid] += qty
            product_tot_val[pid] += val
            prod_ids_from_svl.add(pid)

        # Fetch landed costs from the landed_cost_amount field on SVLs
        # This uses our custom field that tracks distributed landed costs per layer
        product_landed_cost = defaultdict(float)
        for svl in regular_svls:
            pid = svl.product_id.id
            if not pid:
                continue

            landed_cost_amt = float(svl.landed_cost_amount or 0.0)
            if abs(landed_cost_amt) > 1e-9:
                product_landed_cost[pid] += landed_cost_amt

        # Calculate average cost WITHOUT landed cost
        avg_cost = {}
        for pid in prod_ids_from_svl:
            total_qty = product_tot_qty[pid]
            if abs(total_qty) > 1e-12:
                avg_cost[pid] = product_tot_val[pid] / total_qty
            else:
                avg_cost[pid] = 0.0

        # Fallback to standard_price
        if product_ids:
            missing_ids = set(product_ids) - set(avg_cost.keys())
            if missing_ids:
                products = self.env['product.product'].browse(list(missing_ids))
                for product in products:
                    if product.id not in avg_cost:
                        avg_cost[product.id] = product.standard_price or 0.0

        return avg_cost, prod_ids_from_svl, dict(product_landed_cost)

    def _compute_quantities(self, end_date_str, prod_ids_from_svl, start_date_str=None):
        """Compute ending quantities per product x location from move lines."""
        MoveLine = self.env['stock.move.line']
        Location = self.env['stock.location']

        ml_domain = [
            ('move_id.state', '=', 'done'),
            ('product_id.active', '=', True),
            ('move_id.date', '<=', end_date_str),
        ]

        # Add start date filter if provided
        if start_date_str:
            ml_domain.append(('move_id.date', '>=', start_date_str))

        # Filter by selected products if any
        filter_product_ids = self.product_ids.ids if self.product_ids else []
        if filter_product_ids:
            ml_domain.append(('product_id', 'in', filter_product_ids))

        move_lines = MoveLine.search(ml_domain)

        prod_ids = set(prod_ids_from_svl)
        for ml in move_lines:
            if ml.product_id:
                prod_ids.add(ml.product_id.id)

        products = self.env['product.product'].browse(list(prod_ids)).filtered(lambda p: p.active)
        prod_map = {p.id: p for p in products}

        # Get locations including children
        location_ids = self.location_ids.ids if self.location_ids else []
        if location_ids:
            # Get all child locations recursively
            selected_locations = self.location_ids
            all_locations = selected_locations
            for loc in selected_locations:
                all_locations |= loc.child_ids
            internal_location_ids = set(all_locations.ids)
        else:
            internal_locations = Location.search([('usage', '=', 'internal')])
            internal_location_ids = set(internal_locations.ids)

        qty_by_prod_loc: Dict[Tuple[int, int], float] = defaultdict(float)

        for ml in move_lines:
            if not ml.product_id or ml.product_id.id not in prod_map:
                continue

            qty_done = float(ml.quantity or 0.0)
            if abs(qty_done) < 1e-12:
                continue

            product = prod_map[ml.product_id.id]

            qty_in_product_uom = self._convert_qty(
                qty_done,
                ml.product_uom_id,
                product.uom_id
            )

            src_id = ml.location_id.id
            dst_id = ml.location_dest_id.id

            if src_id in internal_location_ids:
                qty_by_prod_loc[(ml.product_id.id, src_id)] -= qty_in_product_uom

            if dst_id in internal_location_ids:
                qty_by_prod_loc[(ml.product_id.id, dst_id)] += qty_in_product_uom

        return qty_by_prod_loc, prod_map, internal_location_ids

    def _generate_excel(self, rows, end_date_str):
        """Generate Excel file from snapshot data."""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Stock Snapshot')

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        number_format = workbook.add_format({'num_format': '#,##0.00'})
        qty_format = workbook.add_format({'num_format': '#,##0.000000'})

        headers = ['Product Code', 'Product Name', 'Quantity', 'Amount', 'Landed Cost', 'Total Amount', 'UoM', 'Location', 'Parent Location']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        for row_idx, row_data in enumerate(rows, start=1):
            worksheet.write(row_idx, 0, row_data['product_code'] or '')
            worksheet.write(row_idx, 1, row_data['product_name'] or '')
            worksheet.write(row_idx, 2, row_data['quantity'], qty_format)
            worksheet.write(row_idx, 3, row_data['amount'], number_format)
            worksheet.write(row_idx, 4, row_data.get('landed_cost', 0.0), number_format)
            worksheet.write(row_idx, 5, row_data.get('total_amount', 0.0), number_format)
            worksheet.write(row_idx, 6, row_data['uom_name'] or '')
            worksheet.write(row_idx, 7, row_data['location'] or '')
            worksheet.write(row_idx, 8, row_data.get('parent_location', '') or '')

        worksheet.set_column(0, 0, 15)
        worksheet.set_column(1, 1, 40)
        worksheet.set_column(2, 2, 15)
        worksheet.set_column(3, 3, 15)
        worksheet.set_column(4, 4, 15)
        worksheet.set_column(5, 5, 15)
        worksheet.set_column(6, 6, 10)
        worksheet.set_column(7, 7, 30)
        worksheet.set_column(8, 8, 30)

        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, len(rows), 8)

        workbook.close()
        output.seek(0)

        return output.read()

    def _compute_snapshot_data(self):
        """Compute snapshot data and return rows."""
        self.ensure_one()

        end_date_str = fields.Date.to_string(self.end_date)
        start_date_str = fields.Date.to_string(self.start_date) if self.start_date else None
        filter_product_ids = self.product_ids.ids if self.product_ids else None

        avg_cost, prod_ids_from_svl, product_landed_costs = self._compute_average_costs(end_date_str, filter_product_ids)
        qty_by_prod_loc, prod_map, internal_location_ids = self._compute_quantities(
            end_date_str,
            prod_ids_from_svl,
            start_date_str
        )

        Location = self.env['stock.location']
        rows = []
        products_with_stock = set()

        for (pid, lid), qty in qty_by_prod_loc.items():
            if abs(qty) < 1e-9:
                continue

            product = prod_map.get(pid)
            if not product:
                continue

            if self.product_filter:
                code = product.default_code or ''
                name = product.display_name or ''
                filter_lower = self.product_filter.lower()
                if (filter_lower not in code.lower()) and (filter_lower not in name.lower()):
                    continue

            products_with_stock.add(pid)
            location = Location.browse(lid)
            # Find the top-level internal location (root internal)
            parent_location = False
            if location:
                current = location.location_id
                while current:
                    if current.usage == 'internal':
                        parent_location = current
                    current = current.location_id
            unit_cost = avg_cost.get(pid, 0.0)
            if unit_cost == 0.0:
                unit_cost = product.standard_price or 0.0
            amount = qty * unit_cost
            landed_cost = product_landed_costs.get(pid, 0.0)

            rows.append({
                'product_id': product.id,
                'product_code': product.default_code or '',
                'product_name': product.display_name or '',
                'location_id': lid,
                'location_name': location.complete_name if location else '',
                'parent_location_id': parent_location.id if parent_location else False,
                'parent_location_name': parent_location.complete_name if parent_location else '',
                'quantity': qty,
                'uom_name': product.uom_id.name if product.uom_id else '',
                'unit_cost': unit_cost,
                'amount': amount,
                'landed_cost': landed_cost,
                'total_amount': amount + landed_cost,
            })

        # Add products with zero stock but have landed costs
        for pid, landed_cost in product_landed_costs.items():
            if pid in products_with_stock:
                continue  # Already included above
            if abs(landed_cost) < 1e-9:
                continue  # No landed cost to show

            # Check if product matches filter
            product = prod_map.get(pid)
            if not product:
                product = self.env['product.product'].browse(pid)
                if not product.exists() or not product.active:
                    continue

            if self.product_filter:
                code = product.default_code or ''
                name = product.display_name or ''
                filter_lower = self.product_filter.lower()
                if (filter_lower not in code.lower()) and (filter_lower not in name.lower()):
                    continue

            # Check if product matches selected products filter
            if filter_product_ids and pid not in filter_product_ids:
                continue

            rows.append({
                'product_id': product.id,
                'product_code': product.default_code or '',
                'product_name': product.display_name or '',
                'location_id': False,
                'location_name': 'N/A (Zero Stock)',
                'parent_location_id': False,
                'parent_location_name': '',
                'quantity': 0.0,
                'uom_name': product.uom_id.name if product.uom_id else '',
                'unit_cost': 0.0,
                'amount': 0.0,
                'landed_cost': landed_cost,
                'total_amount': landed_cost,
            })

        rows.sort(key=lambda r: (r['product_code'] or '', r['location_name'] or ''))

        if not rows:
            if start_date_str:
                raise UserError(_('No internal stock found between %s and %s.') % (start_date_str, end_date_str))
            else:
                raise UserError(_('No internal stock found as of %s.') % end_date_str)

        return rows

    def action_view_snapshot(self):
        """Generate and view snapshot in separate tree view."""
        self.ensure_one()

        rows = self._compute_snapshot_data()

        # Delete existing snapshot lines
        self.snapshot_line_ids.unlink()

        # Create snapshot lines
        SnapshotLine = self.env['stock.snapshot.line']
        snapshot_vals_list = [{'wizard_id': self.id, **row} for row in rows]
        SnapshotLine.create(snapshot_vals_list)

        self.write({'state': 'view'})

        end_date_str = fields.Date.to_string(self.end_date)
        start_date_str = fields.Date.to_string(self.start_date) if self.start_date else None

        # Return action to open tree view
        if start_date_str:
            report_name = f'Stock Valuation Snapshot - {start_date_str} to {end_date_str}'
        else:
            report_name = f'Stock Valuation Snapshot - {end_date_str}'
        return {
            'type': 'ir.actions.act_window',
            'name': report_name,
            'res_model': 'stock.snapshot.line',
            'view_mode': 'tree',
            'domain': [('wizard_id', '=', self.id)],
            'target': 'current',
            'context': self.env.context,
        }

    def action_export_excel(self):
        """Export snapshot to Excel."""
        self.ensure_one()

        if not xlsxwriter:
            raise UserError(_('Python library xlsxwriter is required.\nPlease install it: pip install xlsxwriter'))

        # If we already have snapshot lines, use them; otherwise compute
        if self.snapshot_line_ids:
            rows = [{
                'product_code': line.product_code,
                'product_name': line.product_name,
                'quantity': line.quantity,
                'amount': line.amount,
                'landed_cost': line.landed_cost,
                'total_amount': line.total_amount,
                'uom_name': line.uom_name,
                'location': line.location_name,
                'parent_location': line.parent_location_name,
            } for line in self.snapshot_line_ids]
        else:
            data = self._compute_snapshot_data()
            rows = [{
                'product_code': r['product_code'],
                'product_name': r['product_name'],
                'quantity': r['quantity'],
                'amount': r['amount'],
                'landed_cost': r.get('landed_cost', 0.0),
                'total_amount': r.get('total_amount', 0.0),
                'uom_name': r['uom_name'],
                'location': r['location_name'],
                'parent_location': r['parent_location_name'],
            } for r in data]

        end_date_str = fields.Date.to_string(self.end_date)
        start_date_str = fields.Date.to_string(self.start_date) if self.start_date else None
        excel_data = self._generate_excel(rows, end_date_str)

        if start_date_str:
            file_name = f'stock_snapshot_{start_date_str}_to_{end_date_str}.xlsx'
        else:
            file_name = f'stock_snapshot_{end_date_str}.xlsx'
        self.write({
            'file_data': base64.b64encode(excel_data),
            'file_name': file_name,
            'state': 'excel'
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.snapshot.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }

    def action_back_to_draft(self):
        """Return to draft state."""
        self.ensure_one()
        self.snapshot_line_ids.unlink()
        self.write({'state': 'draft', 'file_data': False, 'file_name': False})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.snapshot.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }
