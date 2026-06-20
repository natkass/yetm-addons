# -*- coding: utf-8 -*-
"""
Stock Movement Valuation Wizard - Odoo 17
Generates stock movement valuation report with running balance
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


class StockMovementWizard(models.TransientModel):
    _name = 'stock.movement.wizard'
    _description = 'Stock Movement Valuation Wizard'

    start_date = fields.Date(
        string='Start Date',
        help='Start date for movement report'
    )
    end_date = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.context_today,
        help='End date for movement report'
    )
    product_ids = fields.Many2many(
        'product.product',
        'stock_movement_wizard_product_rel',
        'wizard_id',
        'product_id',
        string='Products',
        domain=[('type', '=', 'product')],
        help='Filter by specific products. Leave empty for all products.'
    )
    location_ids = fields.Many2many(
        'stock.location',
        'stock_movement_wizard_location_rel',
        'wizard_id',
        'location_id',
        string='Locations',
        domain=[('usage', '=', 'internal')],
        help='Filter by specific locations. Leave empty for all internal locations.'
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
    movement_line_ids = fields.One2many(
        'stock.movement.valuation',
        'movement_wizard_id',
        string='Movement Lines'
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

        return avg_cost

    def _get_move_type(self, move):
        """Determine the type of stock move."""
        if not move:
            return 'other'

        picking = move.picking_id
        if picking:
            picking_type = picking.picking_type_id
            if picking_type:
                code = picking_type.code
                if code == 'incoming':
                    return 'purchase'
                elif code == 'outgoing':
                    return 'sale'
                elif code == 'internal':
                    return 'internal'

        if hasattr(move, 'production_id') and move.production_id:
            return 'manufacturing'
        if hasattr(move, 'raw_material_production_id') and move.raw_material_production_id:
            return 'manufacturing'

        if hasattr(move, 'is_inventory') and move.is_inventory:
            return 'adjustment'

        origin = move.origin or ''
        if 'INV:' in str(origin) or 'INV/' in str(origin):
            return 'adjustment'

        src_usage = move.location_id.usage if move.location_id else ''
        dst_usage = move.location_dest_id.usage if move.location_dest_id else ''

        if src_usage == 'supplier' or dst_usage == 'supplier':
            return 'purchase'
        if src_usage == 'customer' or dst_usage == 'customer':
            return 'sale'
        if src_usage == 'production' or dst_usage == 'production':
            return 'manufacturing'
        if src_usage == 'inventory' or dst_usage == 'inventory':
            return 'adjustment'

        return 'other'

    def _compute_opening_balances(self, start_date_str, avg_costs, prod_map, internal_location_ids):
        """Compute opening balances per product and location before start_date."""
        MoveLine = self.env['stock.move.line']

        ml_domain = [
            ('move_id.state', '=', 'done'),
            ('product_id.active', '=', True),
            ('move_id.date', '<', start_date_str),
        ]

        move_lines = MoveLine.search(ml_domain)

        opening_balances: Dict[Tuple[int, int], Dict[str, float]] = defaultdict(lambda: {'qty': 0.0, 'value': 0.0})

        for ml in move_lines:
            if not ml.product_id:
                continue

            pid = ml.product_id.id
            product = prod_map.get(pid) or ml.product_id
            if not product.active:
                continue

            qty_done = float(ml.quantity or 0.0)
            if abs(qty_done) < 1e-12:
                continue

            qty_in_product_uom = self._convert_qty(qty_done, ml.product_uom_id, product.uom_id)
            unit_cost = avg_costs.get(pid, 0.0) or product.standard_price or 0.0

            src_id = ml.location_id.id
            dst_id = ml.location_dest_id.id

            if src_id in internal_location_ids:
                opening_balances[(pid, src_id)]['qty'] -= qty_in_product_uom
                opening_balances[(pid, src_id)]['value'] -= qty_in_product_uom * unit_cost

            if dst_id in internal_location_ids:
                opening_balances[(pid, dst_id)]['qty'] += qty_in_product_uom
                opening_balances[(pid, dst_id)]['value'] += qty_in_product_uom * unit_cost

        return opening_balances

    def _compute_movement_data(self):
        """Compute movement data and create movement lines."""
        self.ensure_one()

        MoveLine = self.env['stock.move.line']
        Location = self.env['stock.location']
        MovementValuation = self.env['stock.movement.valuation']

        start_date_str = fields.Date.to_string(self.start_date) if self.start_date else None
        end_date_str = fields.Date.to_string(self.end_date)

        location_ids = self.location_ids.ids if self.location_ids else []
        filter_product_ids = self.product_ids.ids if self.product_ids else []

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

        ml_domain = [
            ('move_id.state', '=', 'done'),
            ('product_id.active', '=', True),
            ('move_id.date', '<=', end_date_str + ' 23:59:59'),
        ]

        if start_date_str:
            ml_domain.append(('move_id.date', '>=', start_date_str))

        if filter_product_ids:
            ml_domain.append(('product_id', 'in', filter_product_ids))

        move_lines = MoveLine.search(ml_domain, order='move_id asc, id asc')

        all_prod_ids = set()
        for ml in move_lines:
            if ml.product_id:
                all_prod_ids.add(ml.product_id.id)

        products = self.env['product.product'].browse(list(all_prod_ids)).filtered(lambda p: p.active)
        prod_map = {p.id: p for p in products}

        avg_costs = self._compute_average_costs(end_date_str, list(prod_map.keys()))

        # Build a mapping of move_id -> actual unit cost from SVLs for purchase movements
        SVL = self.env['stock.valuation.layer']
        move_ids_list = list(set(ml.move_id.id for ml in move_lines if ml.move_id))
        actual_costs_map = {}
        if move_ids_list:
            svls_for_costs = SVL.search([
                ('stock_move_id', 'in', move_ids_list),
                ('quantity', '!=', 0),
            ])
            # Group by move_id to calculate actual unit cost
            move_svl_data = defaultdict(lambda: {'qty': 0.0, 'value': 0.0})
            for svl in svls_for_costs:
                move_id = svl.stock_move_id.id
                # Only count the base value, not landed cost
                move_svl_data[move_id]['qty'] += abs(svl.quantity or 0.0)
                move_svl_data[move_id]['value'] += abs(svl.value or 0.0)

            for move_id, data in move_svl_data.items():
                if data['qty'] > 0:
                    actual_costs_map[move_id] = data['value'] / data['qty']

        if start_date_str:
            opening_balances = self._compute_opening_balances(
                start_date_str, avg_costs, prod_map, internal_location_ids
            )
        else:
            opening_balances = defaultdict(lambda: {'qty': 0.0, 'value': 0.0})

        self.movement_line_ids.unlink()

        raw_movements = []

        for ml in move_lines:
            if not ml.product_id or ml.product_id.id not in prod_map:
                continue

            qty_done = float(ml.quantity or 0.0)
            if abs(qty_done) < 1e-12:
                continue

            product = prod_map[ml.product_id.id]
            qty_in_product_uom = self._convert_qty(qty_done, ml.product_uom_id, product.uom_id)

            move = ml.move_id
            src_id = ml.location_id.id
            dst_id = ml.location_dest_id.id

            move_type = self._get_move_type(move)

            # For purchase movements, use actual purchase cost; otherwise use average cost
            if move_type == 'purchase' and move.id in actual_costs_map:
                unit_cost = actual_costs_map[move.id]
            else:
                unit_cost = avg_costs.get(product.id, 0.0) or product.standard_price or 0.0

            reference = move.reference or move.name or ''
            origin = move.origin or ''
            partner_name = move.partner_id.name if move.partner_id else ''
            move_date = move.date

            if src_id in internal_location_ids:
                location = Location.browse(src_id)
                # Find the top-level internal location (root internal)
                parent_location = False
                if location:
                    current = location.location_id
                    while current:
                        if current.usage == 'internal':
                            parent_location = current
                        current = current.location_id
                raw_movements.append({
                    'date': move_date,
                    'move_id': move.id,
                    'ml_id': ml.id,
                    'reference': reference,
                    'move_type': move_type,
                    'product_id': product.id,
                    'product_code': product.default_code or '',
                    'product_name': product.display_name or '',
                    'location_id': src_id,
                    'location_name': location.complete_name if location else '',
                    'parent_location_id': parent_location.id if parent_location else False,
                    'parent_location_name': parent_location.complete_name if parent_location else '',
                    'quantity': -qty_in_product_uom,
                    'uom_name': product.uom_id.name if product.uom_id else '',
                    'unit_cost': unit_cost,
                    'origin': origin,
                    'partner_name': partner_name,
                })

            if dst_id in internal_location_ids:
                location = Location.browse(dst_id)
                # Find the top-level internal location (root internal)
                parent_location = False
                if location:
                    current = location.location_id
                    while current:
                        if current.usage == 'internal':
                            parent_location = current
                        current = current.location_id
                raw_movements.append({
                    'date': move_date,
                    'move_id': move.id,
                    'ml_id': ml.id,
                    'reference': reference,
                    'move_type': move_type,
                    'product_id': product.id,
                    'product_code': product.default_code or '',
                    'product_name': product.display_name or '',
                    'location_id': dst_id,
                    'location_name': location.complete_name if location else '',
                    'parent_location_id': parent_location.id if parent_location else False,
                    'parent_location_name': parent_location.complete_name if parent_location else '',
                    'quantity': qty_in_product_uom,
                    'uom_name': product.uom_id.name if product.uom_id else '',
                    'unit_cost': unit_cost,
                    'origin': origin,
                    'partner_name': partner_name,
                })

        # Landed cost rows have been removed - landed costs are now only shown in the column
        # for regular movements (lines 524-535)

        raw_movements.sort(key=lambda x: (x['date'], x['move_id'], x['ml_id']))

        # Build a mapping of move_id -> landed_cost_amount from SVLs
        move_ids = set(mov['move_id'] for mov in raw_movements if mov['move_id'])
        if move_ids:
            svl_domain = [
                ('stock_move_id', 'in', list(move_ids)),
                ('quantity', '!=', 0),  # Regular movements, not landed cost adjustments
            ]
            svls = SVL.search(svl_domain)

            # Map: move_id -> {total_qty, total_landed_cost}
            move_landed_cost_map = defaultdict(lambda: {'qty': 0.0, 'landed_cost': 0.0})
            for svl in svls:
                mid = svl.stock_move_id.id
                move_landed_cost_map[mid]['qty'] += abs(svl.quantity)
                move_landed_cost_map[mid]['landed_cost'] += svl.landed_cost_amount or 0.0
        else:
            move_landed_cost_map = {}

        movements_by_product: Dict[int, list] = defaultdict(list)
        for mov in raw_movements:
            movements_by_product[mov['product_id']].append(mov)

        product_opening_balances: Dict[int, Dict[str, float]] = defaultdict(lambda: {'qty': 0.0, 'value': 0.0})
        for (pid, lid), bal in opening_balances.items():
            product_opening_balances[pid]['qty'] += bal['qty']
            product_opening_balances[pid]['value'] += bal['value']

        movement_vals_list = []
        for pid, movements in movements_by_product.items():
            running_qty = product_opening_balances[pid]['qty']
            running_value = product_opening_balances[pid]['value']
            running_total = product_opening_balances[pid]['value']  # Balance total (value + landed cost)

            movements.sort(key=lambda x: (x['date'], x['move_id'], x['ml_id']))

            for mov in movements:
                qty_change = mov['quantity']
                value_change = qty_change * mov['unit_cost']

                # Calculate landed cost for this movement
                move_id = mov.get('move_id', 0)
                if move_id and move_id in move_landed_cost_map:
                    move_data = move_landed_cost_map[move_id]
                    if move_data['qty'] > 0:
                        # Distribute landed cost proportionally by quantity
                        # landed_cost from SVL is already positive for incoming, negative for outgoing
                        landed_cost_change = (abs(qty_change) / move_data['qty']) * move_data['landed_cost']
                    else:
                        landed_cost_change = 0.0
                else:
                    landed_cost_change = 0.0

                running_qty += qty_change
                running_value += value_change

                # Balance total only updates when quantity is not zero
                if abs(qty_change) > 1e-9:
                    running_total += value_change + landed_cost_change

                movement_vals_list.append({
                    'movement_wizard_id': self.id,
                    'date': mov['date'],
                    'reference': mov['reference'],
                    'move_type': mov['move_type'],
                    'product_id': mov['product_id'],
                    'product_code': mov['product_code'],
                    'product_name': mov['product_name'],
                    'location_id': mov['location_id'],
                    'location_name': mov['location_name'],
                    'parent_location_id': mov['parent_location_id'],
                    'parent_location_name': mov['parent_location_name'],
                    'quantity': qty_change,
                    'uom_name': mov['uom_name'],
                    'unit_cost': mov['unit_cost'],
                    'value': value_change,
                    'landed_cost_amount': landed_cost_change,
                    'total_value': value_change + landed_cost_change,
                    'balance_qty': running_qty,
                    'balance_value': running_value,
                    'balance_total': running_total,
                    'origin': mov['origin'],
                    'partner_name': mov['partner_name'],
                })

        if not movement_vals_list:
            raise UserError(_('No stock movements found for the selected criteria.'))

        MovementValuation.create(movement_vals_list)

    def action_view_movements(self):
        """Generate and view movements in separate tree view."""
        self.ensure_one()

        self._compute_movement_data()
        self.write({'state': 'view'})

        start_str = fields.Date.to_string(self.start_date) if self.start_date else 'All'
        end_str = fields.Date.to_string(self.end_date)

        # Return action to open tree view
        return {
            'type': 'ir.actions.act_window',
            'name': f'Stock Movements - {start_str} to {end_str}',
            'res_model': 'stock.movement.valuation',
            'view_mode': 'tree',
            'domain': [('movement_wizard_id', '=', self.id)],
            'target': 'current',
            'context': self.env.context,
        }

    def action_export_excel(self):
        """Export movements to Excel."""
        self.ensure_one()

        if not xlsxwriter:
            raise UserError(_('Python library xlsxwriter is required.\nPlease install it: pip install xlsxwriter'))

        # If no movement lines exist, compute them first
        if not self.movement_line_ids:
            self._compute_movement_data()

        excel_data = self._generate_excel()

        start_str = fields.Date.to_string(self.start_date) if self.start_date else 'all'
        end_str = fields.Date.to_string(self.end_date)
        file_name = f'stock_movements_{start_str}_to_{end_str}.xlsx'

        self.write({
            'file_data': base64.b64encode(excel_data),
            'file_name': file_name,
            'state': 'excel'
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.movement.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }

    def _generate_excel(self):
        """Generate Excel file from movement valuation data."""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Stock Movements')

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
        number_format = workbook.add_format({'num_format': '#,##0.00'})
        qty_format = workbook.add_format({'num_format': '#,##0.000000'})
        negative_format = workbook.add_format({'num_format': '#,##0.000000', 'font_color': 'red'})
        negative_value_format = workbook.add_format({'num_format': '#,##0.00', 'font_color': 'red'})

        headers = [
            'Date', 'Reference', 'Type', 'Product Code', 'Product Name',
            'Location', 'Parent Location', 'Quantity', 'UoM', 'Unit Cost', 'Value',
            'Landed Cost', 'Total Value', 'Balance Qty', 'Balance Value', 'Balance Total',
            'Source Document', 'Partner'
        ]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        for row_idx, line in enumerate(self.movement_line_ids, start=1):
            worksheet.write(row_idx, 0, line.date, date_format)
            worksheet.write(row_idx, 1, line.reference or '')
            worksheet.write(row_idx, 2, dict(line._fields['move_type'].selection).get(line.move_type, ''))
            worksheet.write(row_idx, 3, line.product_code or '')
            worksheet.write(row_idx, 4, line.product_name or '')
            worksheet.write(row_idx, 5, line.location_name or '')
            worksheet.write(row_idx, 6, line.parent_location_name or '')

            if line.quantity < 0:
                worksheet.write(row_idx, 7, line.quantity, negative_format)
            else:
                worksheet.write(row_idx, 7, line.quantity, qty_format)

            worksheet.write(row_idx, 8, line.uom_name or '')
            worksheet.write(row_idx, 9, line.unit_cost, number_format)

            if line.value < 0:
                worksheet.write(row_idx, 10, line.value, negative_value_format)
            else:
                worksheet.write(row_idx, 10, line.value, number_format)

            if line.landed_cost_amount < 0:
                worksheet.write(row_idx, 11, line.landed_cost_amount, negative_value_format)
            else:
                worksheet.write(row_idx, 11, line.landed_cost_amount, number_format)

            if line.total_value < 0:
                worksheet.write(row_idx, 12, line.total_value, negative_value_format)
            else:
                worksheet.write(row_idx, 12, line.total_value, number_format)

            worksheet.write(row_idx, 13, line.balance_qty, qty_format)
            worksheet.write(row_idx, 14, line.balance_value, number_format)
            worksheet.write(row_idx, 15, line.balance_total, number_format)
            worksheet.write(row_idx, 16, line.origin or '')
            worksheet.write(row_idx, 17, line.partner_name or '')

        worksheet.set_column(0, 0, 20)
        worksheet.set_column(1, 1, 20)
        worksheet.set_column(2, 2, 15)
        worksheet.set_column(3, 3, 15)
        worksheet.set_column(4, 4, 35)
        worksheet.set_column(5, 5, 30)
        worksheet.set_column(6, 6, 30)
        worksheet.set_column(7, 7, 15)
        worksheet.set_column(8, 8, 10)
        worksheet.set_column(9, 9, 12)
        worksheet.set_column(10, 10, 15)
        worksheet.set_column(11, 11, 15)
        worksheet.set_column(12, 12, 15)
        worksheet.set_column(13, 13, 15)
        worksheet.set_column(14, 14, 15)
        worksheet.set_column(15, 15, 15)
        worksheet.set_column(16, 16, 20)
        worksheet.set_column(17, 17, 25)

        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, len(self.movement_line_ids), 17)

        workbook.close()
        output.seek(0)

        return output.read()

    def action_back_to_draft(self):
        """Return to draft state."""
        self.ensure_one()
        self.write({'state': 'draft', 'file_data': False, 'file_name': False})
        self.movement_line_ids.unlink()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.movement.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }
