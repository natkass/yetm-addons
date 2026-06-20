# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
import random
from odoo.tools import float_is_zero
import json
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict

import logging

_logger = logging.getLogger(__name__)


class pos_config(models.Model):
    _inherit = 'pos.config'

    def _get_default_location(self):
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)],
                                                  limit=1).lot_stock_id

    pos_display_stock = fields.Boolean(string='Display Stock in POS')
    pos_stock_type = fields.Selection(
        [('onhand', 'Qty on Hand'),('available', 'Qty Available')], default='onhand', string='Stock Type', help='Seller can display Different stock type in POS.')
    pos_allow_order = fields.Boolean(string='Allow POS Order When Product is Out of Stock')
    pos_deny_order = fields.Char(string='Deny POS Order When Product Qty is goes down to')
    stock_position = fields.Selection(
        [('top_right', 'Top Right'), ('top_left', 'Top Left'), ('bottom_right', 'Bottom Right')], default='top_left', string='Stock Position')

    show_stock_location = fields.Selection([
        ('all', 'All Warehouse'),
        ('specific', 'Current Session Warehouse'),
    ], string='Show Stock Of', default='all')

    stock_location_id = fields.Many2one(
        'stock.location', string='Stock Location',
        domain=[('usage', '=', 'internal')], required=True, default=_get_default_location)
    
    color_background = fields.Char(
        string='Color',)
    font_background = fields.Char(
        string='Font Color',)
    low_stock = fields.Float(
        string='Product Low Stock',default=0.00)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_display_stock = fields.Boolean(related="pos_config_id.pos_display_stock",readonly=False)
    pos_stock_type = fields.Selection(related="pos_config_id.pos_stock_type", readonly=False,string='Stock Type', help='Seller can display Different stock type in POS.')
    pos_allow_order = fields.Boolean(string='Allow POS Order When Product is Out of Stock',readonly=False,related="pos_config_id.pos_allow_order")
    pos_deny_order = fields.Char(string='Deny POS Order When Product Qty is goes down to',readonly=False,related="pos_config_id.pos_deny_order")

    show_stock_location = fields.Selection(string='Show Stock Of',readonly=False, related="pos_config_id.show_stock_location")

    stock_location_id = fields.Many2one(
        'stock.location', string='Stock Location',
        domain=[('usage', '=', 'internal')], related="pos_config_id.stock_location_id",readonly=False)
    stock_position = fields.Selection(related="pos_config_id.stock_position", readonly=False,string='Stock Position')
    color_background = fields.Char(string='Background Color',readonly=False,related="pos_config_id.color_background")
    font_background = fields.Char(string='Font Color',readonly=False,related="pos_config_id.font_background")
    low_stock = fields.Float(string='Product Low Stock',readonly=False,related="pos_config_id.low_stock")


class pos_order(models.Model):
    _inherit = 'pos.order'

    location_id = fields.Many2one(
        comodel_name='stock.location',
        related='config_id.stock_location_id',
        string="Location", store=True,
        readonly=True,
    )


class stock_quant(models.Model):
    _inherit = 'stock.move'

    @api.model
    def sync_product(self, prd_id):
        notifications = []
        ssn_obj = self.env['pos.session'].sudo()
        prod_fields = ssn_obj._loader_params_product_product()['search_params']['fields']
        prod_obj = self.env['product.product'].sudo()

        # Perform the search_read operation
        product = prod_obj.with_context(display_default_code=False).search_read([('id', '=', prd_id)], prod_fields)
        
        # Ensure that the product list is not empty
        if not product:
            return True  # Or handle the situation differently if needed

        product_id = prod_obj.search([('id', '=', prd_id)])
        
        # Compute the quantities
        res = product_id._compute_quantities_dict(
            self._context.get('lot_id'), 
            self._context.get('owner_id'), 
            self._context.get('package_id'), 
            self._context.get('from_date'), 
            self._context.get('to_date')
        )
        
        # Update qty_available based on the computed quantities
        if product_id.id in res:
            product[0]['qty_available'] = res[product_id.id]['qty_available']
        else:
            product[0]['qty_available'] = 0  # Default value

        # Further processing if product exists
        if product:
            categories = ssn_obj._get_pos_ui_product_category(ssn_obj._loader_params_product_category())
            product_category_by_id = {category['id']: category for category in categories}
            product[0]['categ'] = product_category_by_id[product[0]['categ_id'][0]]

            vals = {
                'id': [product[0].get('id')], 
                'product': product,
                'access': 'pos.sync.product',
            }
            notifications.append([self.env.user.partner_id, 'product.product/sync_data', vals])
        
        # Send notifications if there are any
        if notifications:
            self.env['bus.bus']._sendmany(notifications)
        
        return True

    @api.model
    def create(self, vals):
        res = super(stock_quant, self).create(vals)
        notifications = []
        for rec in res:
            rec.sync_product(rec.product_id.id)
        return res

    def write(self, vals):
        res = super(stock_quant, self).write(vals)
        notifications = []
        for rec in self:
            rec.sync_product(rec.product_id.id)
        return res


class ProductInherit(models.Model):
    _inherit = 'product.product'

    quant_text = fields.Text('Quant Qty', compute='_compute_avail_locations', store=True)


    def get_low_stock_products(self,low_stock):
        products=self.search([('detailed_type', '=' ,'product')]);
        product_list=[]
        for product in products:
            if product.qty_available <= low_stock:
                product_list.append(product.id)
        return product_list
    @api.depends('stock_quant_ids', 'stock_quant_ids.product_id', 'stock_quant_ids.location_id',
                 'stock_quant_ids.quantity','stock_quant_ids.available_quantity')
    def _compute_avail_locations(self):
        notifications = []
        for rec in self:
            final_data = {}
            rec.quant_text = json.dumps(final_data)
            if rec.type == 'product':
                quants = self.env['stock.quant'].sudo().search(
                    [('product_id', 'in', rec.ids), ('location_id.usage', '=', 'internal')])
                for quant in quants:
                    loc = quant.location_id.id
                    if loc in final_data:
                        last_qty = final_data[loc][0]
                        final_data[loc][0] = last_qty + quant.quantity
                    else:
                        final_data[loc] = [quant.quantity, 0, 0,quant.available_quantity]
                rec.quant_text = json.dumps(final_data)
        return True


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Kestedemena-specific fields (from first class)
    validated_by = fields.Many2one('res.users', string='Validated By')
    validation_date = fields.Datetime(string='Validation Date')
    validation_notes = fields.Text(string='Validation Notes')
    is_kestedemena_delivery = fields.Boolean(string='Kestedemena Delivery', compute='_compute_is_kestedemena_delivery')

    # Override the name field to ensure it gets proper sequence (from second class)
    name = fields.Char('Reference', default='/', copy=False, index=True, readonly=True)

    @api.depends('pos_order_id.config_id.kestedemena_mode')
    def _compute_is_kestedemena_delivery(self):
        for picking in self:
            # Handle case where pos_order_id field might not exist (if pos_fiscal not installed)
            if hasattr(picking, 'pos_order_id') and picking.pos_order_id and hasattr(picking.pos_order_id.config_id, 'kestedemena_mode'):
                picking.is_kestedemena_delivery = picking.pos_order_id.config_id.kestedemena_mode
            else:
                picking.is_kestedemena_delivery = False

    def action_manual_validate(self):
        """Manual validation for Kestedemena deliveries"""
        for picking in self:
            if picking.state != 'ready':
                raise UserError(_('Only delivery orders in Ready state can be validated.'))

            # Mark delivery as done
            picking.action_confirm()
            picking.button_validate()

            # Update validation info
            picking.write({
                'validated_by': self.env.user.id,
                'validation_date': fields.Datetime.now(),
            })

            # Create stock moves and deduct stock
            for move in picking.move_lines:
                move._action_done()

        return True

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to force proper sequence generation"""
        pickings = super(StockPicking, self).create(vals_list)

        for picking in pickings:
            # Force sequence generation if name is still number or default
            if not picking.name or picking.name == '/' or picking.name.isdigit():
                new_name = self._generate_sequence_name(picking)
                if new_name:
                    picking.write({'name': new_name})
                    _logger.info("FORCED new sequence name: %s for picking ID: %s", new_name, picking.id)

        return pickings

    def _generate_sequence_name(self, picking):
        """Generate proper sequence name based on picking type and warehouse"""
        picking_type = picking.picking_type_id
        if not picking_type:
            return False

        # Get warehouse code (branch name)
        warehouse = picking_type.warehouse_id
        branch_code = warehouse.code if warehouse and warehouse.code else 'MAIN'

        # Determine sequence based on picking type
        if picking_type.code == 'outgoing':
            # Sales orders
            prefix = f'{branch_code}/OUT/'
            sequence_code = f'stock.picking.out.{branch_code.lower()}'
        elif 'pos' in picking_type.name.lower() or picking_type.code == 'pos':
            # POS orders
            prefix = f'{branch_code}/POS/'
            sequence_code = f'stock.picking.pos.{branch_code.lower()}'
        else:
            # Other types
            prefix = f'{branch_code}/{picking_type.code.upper()}/'
            sequence_code = f'stock.picking.{picking_type.code}.{branch_code.lower()}'

        # Find or create sequence
        sequence = self.env['ir.sequence'].sudo().search([('code', '=', sequence_code)], limit=1)

        if not sequence:
            # Create the sequence
            sequence = self.env['ir.sequence'].sudo().create({
                'name': f'{branch_code} {picking_type.name} Sequence',
                'code': sequence_code,
                'prefix': prefix,
                'padding': 5,
                'number_next': 1,
                'company_id': picking_type.company_id.id,
            })
            _logger.info("Created sequence: %s with prefix: %s", sequence_code, prefix)

        # Generate next number
        return sequence.sudo()._next()

    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
        """Enhanced to prevent duplicates between Sales and POS"""
        _logger.info("=== POS PICKING CREATION ===")
        _logger.info("Picking Type: %s", picking_type.name)

        pickings = self.with_context(disable_duplicate_check=False)

        stockable_lines = lines.filtered(
            lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty, precision_rounding=l.product_id.uom_id.rounding)
        )
        if not stockable_lines:
            _logger.info("No stockable lines found for POS order. Returning empty pickings.")
            return pickings

        positive_lines = stockable_lines.filtered(lambda l: l.qty > 0)
        negative_lines = stockable_lines - positive_lines

        # Process positive lines (outgoing deliveries)
        if positive_lines:
            location_id = positive_lines[0].order_id.location_id.id
            product_ids = [line.product_id.id for line in positive_lines]
            customer = partner or positive_lines[0].order_id.partner_id

            _logger.info("=== CHECKING FOR DUPLICATES ===")
            _logger.info("Customer: %s (ID: %s)", customer.name if customer else "Walk-in", customer.id if customer else "None")
            _logger.info("Products: %s", product_ids)

            with self.env.cr.savepoint():
                self.env.cr.execute("LOCK TABLE stock_picking IN EXCLUSIVE MODE")
                existing_picking = self._find_existing_picking_for_customer_product(customer, picking_type, product_ids)

                if existing_picking:
                    _logger.info("DUPLICATE PREVENTED: Reusing existing picking %s", existing_picking.name)
                    pickings |= existing_picking
                else:
                    _logger.info("Creating new picking for POS order")
                    vals = {
                        'partner_id': customer.id if customer else False,
                        'picking_type_id': picking_type.id,
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'origin': positive_lines[0].order_id.name,
                        'state': 'draft',
                    }

                    positive_picking = self.create(vals)

                    # Link to POS order if pos_order_id field exists (from pos_fiscal module)
                    if hasattr(positive_picking, 'pos_order_id'):
                        positive_picking.write({'pos_order_id': positive_lines[0].order_id.id})

                    positive_picking._create_move_from_pos_order_lines(positive_lines)
                    positive_picking.action_confirm()
                    positive_picking.write({'state': 'waiting'})
                    pickings |= positive_picking

        # Process negative lines (returns)
        if negative_lines:
            return_picking_type = picking_type.return_picking_type_id or picking_type
            return_location_id = return_picking_type.default_location_dest_id.id or picking_type.default_location_src_id.id

            product_ids = [line.product_id.id for line in negative_lines]
            customer = partner or negative_lines[0].order_id.partner_id

            _logger.info("=== CHECKING FOR RETURN DUPLICATES ===")
            _logger.info("Customer: %s", customer.name if customer else "Walk-in")
            _logger.info("Products: %s", product_ids)

            with self.env.cr.savepoint():
                self.env.cr.execute("LOCK TABLE stock_picking IN EXCLUSIVE MODE")
                existing_return_picking = self._find_existing_picking_for_customer_product(customer, return_picking_type, product_ids)

                if existing_return_picking:
                    _logger.info("DUPLICATE PREVENTED: Reusing existing return picking %s", existing_return_picking.name)
                    pickings |= existing_return_picking
                else:
                    _logger.info("Creating new return picking for POS order")
                    vals = {
                        'partner_id': customer.id if customer else False,
                        'picking_type_id': return_picking_type.id,
                        'location_id': location_dest_id,
                        'location_dest_id': return_location_id,
                        'origin': negative_lines[0].order_id.name,
                        'state': 'draft',
                    }

                    negative_picking = self.create(vals)

                    # Link to POS order if pos_order_id field exists (from pos_fiscal module)
                    if hasattr(negative_picking, 'pos_order_id'):
                        negative_picking.write({'pos_order_id': negative_lines[0].order_id.id})

                    negative_picking._create_move_from_pos_order_lines(negative_lines)
                    negative_picking.action_confirm()
                    negative_picking.write({'state': 'waiting'})
                    pickings |= negative_picking

        return pickings

    def _find_existing_picking_for_customer_product(self, partner, picking_type, product_ids):
        """Enhanced helper to find existing pickings for both Sales and POS orders"""
        if not product_ids:
            return None

        # Build search domain
        domain = [
            ('picking_type_id', '=', picking_type.id),
            ('state', 'not in', ['cancel', 'done']),
        ]

        # Add partner filter - handle walk-in customers properly
        if partner:
            domain.append(('partner_id', '=', partner.id))
        else:
            domain.append(('partner_id', '=', False))

        pickings = self.search(domain)

        # Filter by product
        existing_picking = pickings.filtered(
            lambda p: any(m.product_id.id in product_ids for m in p.move_ids)
        )
        if not existing_picking:
            existing_picking = pickings.filtered(
                lambda p: any(m.product_id.id in product_ids for m in p.move_line_ids)
            )

        return existing_picking[0] if existing_picking else None

    @api.model
    def _create_picking_from_sale_order(self, sale_order):
        """Create or reuse picking for Sales orders with proper sequence"""
        _logger.info("=== SALES PICKING CREATION ===")
        _logger.info("Sale Order: %s", sale_order.name)

        pickings = self.env['stock.picking']

        stockable_lines = sale_order.order_line.filtered(
            lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.product_uom_qty, precision_rounding=l.product_id.uom_id.rounding)
        )

        if not stockable_lines:
            _logger.info("No stockable lines found for Sales order %s", sale_order.name)
            return pickings

        product_ids = stockable_lines.mapped('product_id').ids
        picking_type = sale_order.warehouse_id.out_type_id
        customer = sale_order.partner_id

        _logger.info("Customer: %s", customer.name)
        _logger.info("Picking Type: %s", picking_type.name)

        with self.env.cr.savepoint():
            self.env.cr.execute("LOCK TABLE stock_picking IN EXCLUSIVE MODE")
            existing_picking = self._find_existing_picking_for_customer_product(customer, picking_type, product_ids)

            if existing_picking:
                _logger.info("DUPLICATE PREVENTED: Reusing existing picking %s", existing_picking.name)
                pickings |= existing_picking
            else:
                _logger.info("Creating new picking for Sales order %s", sale_order.name)

                vals = {
                    'partner_id': customer.id,
                    'picking_type_id': picking_type.id,
                    'location_id': picking_type.default_location_src_id.id,
                    'location_dest_id': picking_type.default_location_dest_id.id,
                    'origin': sale_order.name,
                    'state': 'draft',
                }

                picking = self.create(vals)

                # Create moves for sale order lines
                for line in stockable_lines:
                    move_vals = {
                        'name': line.product_id.name,
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'picking_id': picking.id,
                        'location_id': picking_type.default_location_src_id.id,
                        'location_dest_id': picking_type.default_location_dest_id.id,
                    }
                    self.env['stock.move'].create(move_vals)

                picking.action_confirm()
                picking.write({'state': 'waiting'})
                pickings |= picking

        return pickings

    # @api.model
    # def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
    #     """We'll create some picking based on order_lines"""

    #     pickings = self.env['stock.picking']
    #     stockable_lines = lines.filtered(
    #         lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty,
    #                                                                                   precision_rounding=l.product_id.uom_id.rounding))
    #     if not stockable_lines:
    #         return pickings
    #     positive_lines = stockable_lines.filtered(lambda l: l.qty > 0)
    #     negative_lines = stockable_lines - positive_lines

    #     if positive_lines:
    #         pos_order = positive_lines[0].order_id
    #         location_id = pos_order.location_id.id
    #         vals = self._prepare_picking_vals(partner, picking_type, location_id, location_dest_id)
    #         positive_picking = self.env['stock.picking'].create(vals)
    #         positive_picking._create_move_from_pos_order_lines(positive_lines)
            
    #         # Kestedemena Business Mode Logic
    #         if pos_order.config_id.kestedemena_mode:
    #             try:
    #                 with self.env.cr.savepoint():
    #                     # Create delivery order in Ready state for manual validation
    #                     positive_picking.action_confirm()
    #                     positive_picking.write({'state': 'ready'})
                        
    #                     # Don't deduct stock immediately - wait for manual validation
    #                     if pos_order.config_id.prevent_stock_deduction:
    #                         # Mark moves as not done to prevent stock deduction
    #                         for move in positive_picking.move_lines:
    #                             move.write({'state': 'confirmed'})
                                
    #             except (UserError, ValidationError):
    #                 pass
    #         else:
    #             # Standard behavior
#             try:
#                 with self.env.cr.savepoint():
    #                     positive_picking.action_confirm()
    #                     positive_picking.write({'state': 'waiting'})
#             except (UserError, ValidationError):
#                 pass

    #         pickings |= positive_picking
            
    #     if negative_lines:
    #         if picking_type.return_picking_type_id:
    #             return_picking_type = picking_type.return_picking_type_id
    #             return_location_id = return_picking_type.default_location_dest_id.id
    #         else:
    #             return_picking_type = picking_type
    #             return_location_id = picking_type.default_location_src_id.id

    #         vals = self._prepare_picking_vals(partner, return_picking_type, location_dest_id, return_location_id)
    #         negative_picking = self.env['stock.picking'].create(vals)
    #         negative_picking._create_move_from_pos_order_lines(negative_lines)
            
    #         # Kestedemena Business Mode Logic for Returns
    #         if negative_lines[0].order_id.config_id.kestedemena_mode:
    #             try:
    #                 with self.env.cr.savepoint():
    #                     negative_picking.action_confirm()
    #                     negative_picking.write({'state': 'ready'})
    #             except (UserError, ValidationError):
    #                 pass
    #         else:
#             try:
#                 with self.env.cr.savepoint():
    #                     negative_picking.action_confirm()
    #                     negative_picking.write({'state': 'waiting'})
#             except (UserError, ValidationError):
#                 pass

    #         pickings |= negative_picking
    #     return pickings


    # @api.model
    # def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
    #     """We'll create some picking based on order_lines"""

    #     import logging
    #     _logger = logging.getLogger(__name__)

    #     pickings = self.env['stock.picking']

    #     # --- START NEW CODE: Find related sale order ---
    #     stockable_lines = lines.filtered(
    #     lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty, precision_rounding=l.product_id.uom_id.rounding)
    # )

    #     if not stockable_lines:
    #           return pickings

    #     positive_lines = stockable_lines.filtered(lambda l: l.qty > 0)
    #     negative_lines = stockable_lines - positive_lines

    # # --- START NEW CODE: Find related sale order ---
    #     pos_order = positive_lines[0].order_id if positive_lines else negative_lines[0].order_id
    #     sale_order = False
    #     if hasattr(pos_order, 'sale_order_id') and pos_order.sale_order_id:
    #        sale_order = pos_order.sale_order_id
    #     elif hasattr(pos_order, 'config_id') and pos_order.config_id:
    #         sale_order = self.env['sale.order'].search([('pos_config_id', '=', pos_order.config_id.id)], limit=1)
    #     else:
    #         _logger.warning("No sale order found for POS order %s", pos_order.name)
#         return pickings

    # # --- END NEW CODE ---

    # # ---------- POSITIVE LINES ----------
    #     if positive_lines:
    #      location_id = pos_order.location_id.id

    #     # --- Check for existing picking ---
    #     existing_picking = self.env['stock.picking'].search([
    #         ('sale_id', '=', sale_order.id if sale_order else False),
    #         ('picking_type_id', '=', picking_type.id),
    #         ('state', 'not in', ['cancel', 'done'])
    #     ], limit=1)

    #     if existing_picking:
    #         _logger.info(
    #             "Skipping picking creation for POS order %s as a picking (%s) already exists from sale order %s.",
    #             pos_order.name, existing_picking.name, sale_order.name if sale_order else 'N/A'
    #         )
    #         pickings |= existing_picking
    #     else:
    #         vals = self._prepare_picking_vals(partner, picking_type, location_id, location_dest_id)
    #         positive_picking = self.env['stock.picking'].create(vals)
    #         positive_picking.write({
    #             'pos_order_id': pos_order.id,
    #             'sale_id': sale_order.id if sale_order else False
    #         })
    #         positive_picking._create_move_from_pos_order_lines(positive_lines)

    #         # Kestedemena Business Mode Logic
    #         if pos_order.config_id.kestedemena_mode:
    #             try:
    #                 with self.env.cr.savepoint():
    #                     positive_picking.action_confirm()
    #                     positive_picking.write({'state': 'ready'})

    #                     if pos_order.config_id.prevent_stock_deduction:
    #                         for move in positive_picking.move_lines:
    #                             move.write({'state': 'confirmed'})
    #             except (UserError, ValidationError) as e:
    #                 _logger.error("Error in kestedemena mode for positive picking: %s", str(e))
    #         else:
    #             try:
    #                 with self.env.cr.savepoint():
    #                     positive_picking.action_confirm()
    #                     positive_picking.write({'state': 'waiting'})
    #             except (UserError, ValidationError) as e:
    #                 _logger.error("Error in standard mode for positive picking: %s", str(e))

    #         pickings |= positive_picking

    # # ---------- NEGATIVE LINES ----------
    #     if negative_lines:
    #         if picking_type.return_picking_type_id:
    #          return_picking_type = picking_type.return_picking_type_id
    #         return_location_id = return_picking_type.default_location_dest_id.id
    #     else:
    #         return_picking_type = picking_type
    #         return_location_id = picking_type.default_location_src_id.id

    #     # --- Check for existing return picking ---
    #     existing_return_picking = self.env['stock.picking'].search([
    #         ('sale_id', '=', sale_order.id if sale_order else False),
    #         ('picking_type_id', '=', return_picking_type.id),
    #         ('state', 'not in', ['cancel', 'done'])
    #     ], limit=1)

    #     if existing_return_picking:
    #         _logger.info(
    #             "Skipping return picking creation for POS order %s as a picking (%s) already exists from sale order %s.",
    #             pos_order.name, existing_return_picking.name, sale_order.name if sale_order else 'N/A'
    #         )
    #         pickings |= existing_return_picking
    #     else:
    #         vals = self._prepare_picking_vals(partner, return_picking_type, location_dest_id, return_location_id)
    #         negative_picking = self.env['stock.picking'].create(vals)
    #         negative_picking.write({
    #             'pos_order_id': pos_order.id,
    #             'sale_id': sale_order.id if sale_order else False
    #         })
    #         negative_picking._create_move_from_pos_order_lines(negative_lines)

    #         if pos_order.config_id.kestedemena_mode:
    #             try:
    #                 with self.env.cr.savepoint():
    #                     negative_picking.action_confirm()
    #                     negative_picking.write({'state': 'ready'})
    #             except (UserError, ValidationError) as e:
    #                 _logger.error("Error in kestedemena mode for negative picking: %s", str(e))
    #         else:
    #             try:
    #                 with self.env.cr.savepoint():
    #                     negative_picking.action_confirm()
    #                     negative_picking.write({'state': 'waiting'})
    #             except (UserError, ValidationError) as e:
    #                 _logger.error("Error in standard mode for negative picking: %s", str(e))

    #         pickings |= negative_picking

    #     return pickings



# import logging
# from odoo import api, models

# _logger = logging.getLogger(__name__)

# class StockPicking(models.Model):
#     _inherit = 'stock.picking'

#     def _find_existing_picking_for_customer_product(self, partner, picking_type, product_ids):
#         """Enhanced helper to find existing pickings for both Sales and POS orders"""
#         partner_name = partner.name.lower().strip() if partner and partner.name else False
#         similar_partners = self.env['res.partner'].search([
#             '|', ('name', 'ilike', partner_name),
#             ('commercial_partner_id', '=', partner.commercial_partner_id.id if partner else False),
#             ('id', '!=', partner.id if partner else False)
#         ], limit=5) if partner_name else False
        
#         # Include pickings from the same warehouse to handle Sales and POS overlap
#         warehouse = picking_type.warehouse_id
#         related_picking_types = self.env['stock.picking.type'].search([
#             ('warehouse_id', '=', warehouse.id),
#             ('code', 'in', ['outgoing', 'internal'])  # Adjust based on your setup
#         ])
        
#         # Use move_ids instead of move_lines for Odoo 17 compatibility
#         domain = [
#             '|', ('partner_id', 'in', similar_partners.ids if similar_partners else [partner.id if partner else False]),
#             ('partner_id', '=', False),
#             ('picking_type_id', 'in', related_picking_types.ids),
#             ('state', 'not in', ['cancel', 'done']),
#         ]
#         # Add a subquery or manual check for move_ids.product_id
#         pickings = self.search(domain)
#         existing_picking = pickings.filtered(lambda p: any(m.product_id.id in product_ids for m in p.move_ids))
#         if not existing_picking:
#             existing_picking = pickings.filtered(lambda p: any(m.product_id.id in product_ids for m in p.move_line_ids))
        
#         _logger.info("Searching for existing picking with domain: %s", domain)
#         _logger.info("Found existing picking: %s (Picking Type: %s)", 
#                      existing_picking.name if existing_picking else "None", 
#                      existing_picking.picking_type_id.name if existing_picking else "N/A")
    
#         return existing_picking[0] if existing_picking else None

#     @api.model
#     def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
#         """Enhanced to prevent duplicates between Sales and POS"""
#         _logger = logging.getLogger(__name__)
#         pickings = self.with_context(disable_duplicate_check=False)
        
#         stockable_lines = lines.filtered(
#             lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty, precision_rounding=l.product_id.uom_id.rounding)
#         )
#         if not stockable_lines:
#             _logger.info("No stockable lines found for POS order. Returning empty pickings.")
#             return pickings
            
#         positive_lines = stockable_lines.filtered(lambda l: l.qty > 0)
#         negative_lines = stockable_lines - positive_lines
        
#         # Process positive lines (outgoing deliveries)
#         if positive_lines:
#             location_id = positive_lines[0].order_id.location_id.id
#             product_ids = [line.product_id.id for line in positive_lines]
#             customer = partner or positive_lines[0].order_id.partner_id
            
#             _logger.info("=== CHECKING FOR DUPLICATES ===")
#             _logger.info("Customer: %s (ID: %s)", customer.name, customer.id)
#             _logger.info("Products: %s", product_ids)
#             _logger.info("Picking Type: %s", picking_type.name)
        
#             with self.env.cr.savepoint():
#                 self.env.cr.execute("LOCK TABLE stock_picking IN SHARE MODE")
#                 existing_picking = self._find_existing_picking_for_customer_product(customer, picking_type, product_ids)
                
#                 if existing_picking:
#                     _logger.info("DUPLICATE PREVENTED: Reusing existing picking %s for customer %s and products %s.", 
#                                  existing_picking.name, customer.name, product_ids)
#                     if positive_lines[0].order_id.id not in existing_picking.mapped('pos_order_id.id'):
#                         existing_picking.write({'pos_order_id': [(4, positive_lines[0].order_id.id)]})
#                     origin_text = existing_picking.origin or ""
#                     pos_order_name = positive_lines[0].order_id.name
#                     if pos_order_name not in origin_text:
#                         existing_picking.write({
#                             'origin': f"{origin_text}, {pos_order_name}" if origin_text else pos_order_name
#                         })
#                     if existing_picking.state == 'waiting':
#                         existing_picking.write({'state': 'waiting'})
#                     pickings |= existing_picking
#                 else:
#                     _logger.info("Creating new picking for POS order %s", positive_lines[0].order_id.name)
#                     vals = self._prepare_picking_vals(customer, picking_type, location_id, location_dest_id)
#                     positive_picking = self.create(vals)
#                     positive_picking.write({'pos_order_id': [(4, positive_lines[0].order_id.id)]})
#                     positive_picking._create_move_from_pos_order_lines(positive_lines)
#                     positive_picking.action_confirm()
#                     positive_picking.write({'state': 'waiting'})
#                     pickings |= positive_picking
                    
#         # Process negative lines (returns)
#         if negative_lines:
#             return_picking_type = picking_type
#             return_location_id = picking_type.default_location_src_id.id
#             if picking_type.return_picking_type_id:
#                 return_picking_type = picking_type.return_picking_type_id
#                 return_location_id = return_picking_type.default_location_dest_id.id or picking_type.default_location_src_id.id
            
#             product_ids = [line.product_id.id for line in negative_lines]
#             customer = partner or negative_lines[0].order_id.partner_id
            
#             _logger.info("=== CHECKING FOR RETURN DUPLICATES ===")
#             _logger.info("Customer: %s (ID: %s)", customer.name, customer.id)
#             _logger.info("Products: %s", product_ids)
#             _logger.info("Return Picking Type: %s", return_picking_type.name)
        
#             with self.env.cr.savepoint():
#                 self.env.cr.execute("LOCK TABLE stock_picking IN SHARE MODE")
#                 existing_return_picking = self._find_existing_picking_for_customer_product(customer, return_picking_type, product_ids)
                
#                 if existing_return_picking:
#                     _logger.info("DUPLICATE PREVENTED: Reusing existing return picking %s for customer %s and products %s.", 
#                                  existing_return_picking.name, customer.name, product_ids)
#                     if negative_lines[0].order_id.id not in existing_return_picking.mapped('pos_order_id.id'):
#                         existing_return_picking.write({'pos_order_id': [(4, negative_lines[0].order_id.id)]})
#                     origin_text = existing_return_picking.origin or ""
#                     pos_order_name = negative_lines[0].order_id.name
#                     if pos_order_name not in origin_text:
#                         existing_return_picking.write({
#                             'origin': f"{origin_text}, {pos_order_name}" if origin_text else pos_order_name
#                         })
#                     pickings |= existing_return_picking
#                 else:
#                     _logger.info("Creating new return picking for POS order %s", negative_lines[0].order_id.name)
#                     vals = self._prepare_picking_vals(customer, return_picking_type, location_dest_id, return_location_id)
#                     negative_picking = self.create(vals)
#                     negative_picking.write({'pos_order_id': [(4, negative_lines[0].order_id.id)]})
#                     negative_picking._create_move_from_pos_order_lines(negative_lines)
#                     negative_picking.action_confirm()
#                     negative_picking.write({'state': 'waiting'})
#                     pickings |= negative_picking
                    
#         return pickings

#     @api.model
#     def _create_picking_from_sale_order(self, sale_order):
#         """Create or reuse picking for Sales orders with duplicate check"""
#         _logger = logging.getLogger(__name__)
#         pickings = self.env['stock.picking']
        
#         stockable_lines = sale_order.order_line.filtered(
#             lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.product_uom_qty, precision_rounding=l.product_id.uom_id.rounding)
#         )
        
#         if not stockable_lines:
#             _logger.info("No stockable lines found for Sales order %s", sale_order.name)
#             return pickings
            
#         product_ids = stockable_lines.mapped('product_id').ids
#         picking_type = sale_order.warehouse_id.out_type_id
#         customer = sale_order.partner_id
        
#         _logger.info("=== SALES ORDER DUPLICATE CHECK ===")
#         _logger.info("Customer: %s (ID: %s)", customer.name, customer.id)
#         _logger.info("Products: %s", product_ids)
#         _logger.info("Picking Type: %s", picking_type.name)
        
#         with self.env.cr.savepoint():
#             self.env.cr.execute("LOCK TABLE stock_picking IN SHARE MODE")
#             existing_picking = self._find_existing_picking_for_customer_product(customer, picking_type, product_ids)
            
#             if existing_picking:
#                 _logger.info("DUPLICATE PREVENTED: Reusing existing picking %s for customer %s and products %s.", 
#                              existing_picking.name, customer.name, product_ids)
#                 if sale_order.id not in existing_picking.mapped('sale_id.id'):
#                     existing_picking.write({'sale_id': [(4, sale_order.id)]})
#                 origin_text = existing_picking.origin or ""
#                 if sale_order.name not in origin_text:
#                     existing_picking.write({
#                         'origin': f"{origin_text}, {sale_order.name}" if origin_text else sale_order.name
#                     })
#                 if existing_picking.state == 'waiting':
#                     existing_picking.write({'state': 'waiting'})
#                 pickings |= existing_picking
#             else:
#                 _logger.info("Creating new picking for Sales order %s", sale_order.name)
#                 picking = sale_order._create_picking()
#                 picking.write({'state': 'waiting'})
#                 pickings |= picking
                
#         return pickings


# import logging
# from odoo import api, fields, models
# from odoo.tools import float_is_zero

# _logger = logging.getLogger(__name__)

# class StockPicking(models.Model):
#     _inherit = 'stock.picking'
    
#     # Override the name field to ensure it gets proper sequence
#     name = fields.Char(
#         'Reference', default='/', copy=False, index=True, readonly=True)
    
#     @api.model_create_multi
#     def create(self, vals_list):
#         """Override create to force proper sequence generation"""
#         pickings = super(StockPicking, self).create(vals_list)
        
#         for picking in pickings:
#             # Force sequence generation if name is still number or default
#             if not picking.name or picking.name == '/' or picking.name.isdigit():
#                 new_name = self._generate_sequence_name(picking)
#                 if new_name:
#                     picking.write({'name': new_name})
#                     _logger.info("FORCED new sequence name: %s for picking ID: %s", new_name, picking.id)
        
#         return pickings
    
#     def _generate_sequence_name(self, picking):
#         """Generate proper sequence name based on picking type and warehouse"""
#         picking_type = picking.picking_type_id
#         if not picking_type:
#             return False
            
#         # Get warehouse code (branch name)
#         warehouse = picking_type.warehouse_id
#         branch_code = warehouse.code if warehouse and warehouse.code else 'MAIN'
        
#         # Determine sequence based on picking type
#         if picking_type.code == 'outgoing':
#             # Sales orders
#             prefix = f'{branch_code}/OUT/'
#             sequence_code = f'stock.picking.out.{branch_code.lower()}'
#         elif 'pos' in picking_type.name.lower() or picking_type.code == 'pos':
#             # POS orders  
#             prefix = f'{branch_code}/POS/'
#             sequence_code = f'stock.picking.pos.{branch_code.lower()}'
#         else:
#             # Other types
#             prefix = f'{branch_code}/{picking_type.code.upper()}/'
#             sequence_code = f'stock.picking.{picking_type.code}.{branch_code.lower()}'
        
#         # Find or create sequence
#         sequence = self.env['ir.sequence'].sudo().search([('code', '=', sequence_code)], limit=1)
        
#         if not sequence:
#             # Create the sequence
#             sequence = self.env['ir.sequence'].sudo().create({
#                 'name': f'{branch_code} {picking_type.name} Sequence',
#                 'code': sequence_code,
#                 'prefix': prefix,
#                 'padding': 5,
#                 'number_next': 1,
#                 'company_id': picking_type.company_id.id,
#             })
#             _logger.info("Created sequence: %s with prefix: %s", sequence_code, prefix)
        
#         # Generate next number
#         return sequence.sudo()._next()
    
#     @api.model
#     def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
#         """Enhanced to prevent duplicates between Sales and POS"""
#         _logger.info("=== POS PICKING CREATION ===")
#         _logger.info("Picking Type: %s", picking_type.name)
        
#         pickings = self.with_context(disable_duplicate_check=False)
        
#         stockable_lines = lines.filtered(
#             lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty, precision_rounding=l.product_id.uom_id.rounding)
#         )
#         if not stockable_lines:
#             _logger.info("No stockable lines found for POS order. Returning empty pickings.")
#             return pickings
            
#         positive_lines = stockable_lines.filtered(lambda l: l.qty > 0)
#         negative_lines = stockable_lines - positive_lines
        
#         # Process positive lines (outgoing deliveries)
#         if positive_lines:
#             location_id = positive_lines[0].order_id.location_id.id
#             product_ids = [line.product_id.id for line in positive_lines]
#             customer = partner or positive_lines[0].order_id.partner_id
            
#             _logger.info("=== CHECKING FOR DUPLICATES ===")
#             _logger.info("Customer: %s (ID: %s)", customer.name if customer else "Walk-in", customer.id if customer else "None")
#             _logger.info("Products: %s", product_ids)
        
#             with self.env.cr.savepoint():
#                 self.env.cr.execute("LOCK TABLE stock_picking IN SHARE MODE")
#                 existing_picking = self._find_existing_picking_for_customer_product(customer, picking_type, product_ids)
                
#                 if existing_picking:
#                     _logger.info("DUPLICATE PREVENTED: Reusing existing picking %s", existing_picking.name)
#                     pickings |= existing_picking
#                 else:
#                     _logger.info("Creating new picking for POS order")
#                     vals = {
#                         'partner_id': customer.id if customer else False,
#                         'picking_type_id': picking_type.id,
#                         'location_id': location_id,
#                         'location_dest_id': location_dest_id,
#                         'origin': positive_lines[0].order_id.name,
#                         'state': 'draft',
#                     }
                    
#                     positive_picking = self.create(vals)
#                     positive_picking._create_move_from_pos_order_lines(positive_lines)
#                     positive_picking.action_confirm()
#                     positive_picking.write({'state': 'waiting'})
#                     pickings |= positive_picking
                    
#         # Process negative lines (returns)
#         if negative_lines:
#             return_picking_type = picking_type.return_picking_type_id or picking_type
#             return_location_id = return_picking_type.default_location_dest_id.id or picking_type.default_location_src_id.id
            
#             product_ids = [line.product_id.id for line in negative_lines]
#             customer = partner or negative_lines[0].order_id.partner_id
            
#             _logger.info("=== CHECKING FOR RETURN DUPLICATES ===")
#             _logger.info("Customer: %s", customer.name if customer else "Walk-in")
#             _logger.info("Products: %s", product_ids)
        
#             with self.env.cr.savepoint():
#                 self.env.cr.execute("LOCK TABLE stock_picking IN SHARE MODE")
#                 existing_return_picking = self._find_existing_picking_for_customer_product(customer, return_picking_type, product_ids)
                
#                 if existing_return_picking:
#                     _logger.info("DUPLICATE PREVENTED: Reusing existing return picking %s", existing_return_picking.name)
#                     pickings |= existing_return_picking
#                 else:
#                     _logger.info("Creating new return picking for POS order")
#                     vals = {
#                         'partner_id': customer.id if customer else False,
#                         'picking_type_id': return_picking_type.id,
#                         'location_id': location_dest_id,
#                         'location_dest_id': return_location_id,
#                         'origin': negative_lines[0].order_id.name,
#                         'state': 'draft',
#                     }
                    
#                     negative_picking = self.create(vals)
#                     negative_picking._create_move_from_pos_order_lines(negative_lines)
#                     negative_picking.action_confirm()
#                     negative_picking.write({'state': 'waiting'})
#                     pickings |= negative_picking
                    
#         return pickings

#     def _find_existing_picking_for_customer_product(self, partner, picking_type, product_ids):
#         """Enhanced helper to find existing pickings for both Sales and POS orders"""
#         if not partner or not product_ids:
#             return None
            
#         partner_name = partner.name.lower().strip() if partner and partner.name else False
#         similar_partners = self.env['res.partner'].search([
#             '|', ('name', 'ilike', partner_name),
#             ('commercial_partner_id', '=', partner.commercial_partner_id.id if partner else False),
#             ('id', '!=', partner.id if partner else False)
#         ], limit=5) if partner_name else []
        
#         # Include pickings from the same warehouse
#         warehouse = picking_type.warehouse_id
#         related_picking_types = self.env['stock.picking.type'].search([
#             ('warehouse_id', '=', warehouse.id),
#             ('code', 'in', ['outgoing', 'internal'])
#         ])
        
#         domain = [
#             '|', ('partner_id', 'in', similar_partners.ids if similar_partners else [partner.id]),
#             ('partner_id', '=', False),
#             ('picking_type_id', 'in', related_picking_types.ids),
#             ('state', 'not in', ['cancel', 'done']),
#         ]
        
#         pickings = self.search(domain)
#         existing_picking = pickings.filtered(lambda p: any(m.product_id.id in product_ids for m in p.move_ids))
#         if not existing_picking:
#             existing_picking = pickings.filtered(lambda p: any(m.product_id.id in product_ids for m in p.move_line_ids))
        
#         return existing_picking[0] if existing_picking else None

#     @api.model
#     def _create_picking_from_sale_order(self, sale_order):
#         """Create or reuse picking for Sales orders with proper sequence"""
#         _logger.info("=== SALES PICKING CREATION ===")
#         _logger.info("Sale Order: %s", sale_order.name)
        
#         pickings = self.env['stock.picking']
        
#         stockable_lines = sale_order.order_line.filtered(
#             lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.product_uom_qty, precision_rounding=l.product_id.uom_id.rounding)
#         )
        
#         if not stockable_lines:
#             _logger.info("No stockable lines found for Sales order %s", sale_order.name)
#             return pickings
            
#         product_ids = stockable_lines.mapped('product_id').ids
#         picking_type = sale_order.warehouse_id.out_type_id
#         customer = sale_order.partner_id
        
#         _logger.info("Customer: %s", customer.name)
#         _logger.info("Picking Type: %s", picking_type.name)
        
#         with self.env.cr.savepoint():
#             self.env.cr.execute("LOCK TABLE stock_picking IN SHARE MODE")
#             existing_picking = self._find_existing_picking_for_customer_product(customer, picking_type, product_ids)
            
#             if existing_picking:
#                 _logger.info("DUPLICATE PREVENTED: Reusing existing picking %s", existing_picking.name)
#                 pickings |= existing_picking
#             else:
#                 _logger.info("Creating new picking for Sales order %s", sale_order.name)
                
#                 vals = {
#                     'partner_id': customer.id,
#                     'picking_type_id': picking_type.id,
#                     'location_id': picking_type.default_location_src_id.id,
#                     'location_dest_id': picking_type.default_location_dest_id.id,
#                     'origin': sale_order.name,
#                     'state': 'draft',
#                 }
                
#                 picking = self.create(vals)
                
#                 # Create moves for sale order lines
#                 for line in stockable_lines:
#                     move_vals = {
#                         'name': line.product_id.name,
#                         'product_id': line.product_id.id,
#                         'product_uom_qty': line.product_uom_qty,
#                         'product_uom': line.product_uom.id,
#                         'picking_id': picking.id,
#                         'location_id': picking_type.default_location_src_id.id,
#                         'location_dest_id': picking_type.default_location_dest_id.id,
#                     }
#                     self.env['stock.move'].create(move_vals)
                
#                 picking.action_confirm()
#                 picking.write({'state': 'waiting'})
#                 pickings |= picking
                
#         return pickings