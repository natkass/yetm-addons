from collections import defaultdict
from distutils.log import error
from itertools import groupby
from re import search
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, OrderedSet
from datetime import timedelta
from datetime import datetime, time
import logging

_logger = logging.getLogger(__name__)


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    allow_confirm_without_qty = fields.Boolean(
        string='Allow Confirm Without Available Qty',
        default=False,
        help="If checked, transfer requests using this operation type can be confirmed even when products are not available in the source location.",
    )


class StockPickingBypass(models.Model):
    _inherit = 'stock.picking'

    def _check_company(self, fnames=None):
        if self.env.context.get('skip_check_company'):
            return
        return super()._check_company(fnames=fnames)


class StockMoveBypass(models.Model):
    _inherit = 'stock.move'

    def _check_company(self, fnames=None):
        if self.env.context.get('skip_check_company'):
            return
        return super()._check_company(fnames=fnames)


class Transfer_request_double(models.Model):
    _name = "transfer.request"
    _description = "Transfer Request"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'product.catalog.mixin']
    name = fields.Char(
        'Reference', default='/',
        copy=False, index=True, readonly=True)
    note = fields.Text('Notes', tracking=True,
        states={'to_check': [('readonly', True)], 'approved': [('readonly', True)], 'partial': [('readonly', True)]})
    state = fields.Selection([
    ('draft', 'Draft'),
    ('to_check', 'To Check'),
    ('approved', 'Confirmed'),
    ('partial', 'Partial'),
    ('done', 'Done'),
    ('cancel', 'Cancelled'),
], string='Status',
    copy=False, index=True, readonly=True, store=True, tracking=True, default="draft")

    date = fields.Datetime(
        'Creation Date',
        default=fields.Datetime.now, index=True, tracking=True,
        help="Creation Date, usually the time of the order",
        states={'to_check': [('readonly', True)], 'approved': [('readonly', True)], 'partial': [('readonly', True)]})
    scheduled_date = fields.Datetime('Scheduled date', default=fields.Datetime.now, copy=False,
                                     help="Date at which the transfer has been processed or cancelled.",
                                     states={'to_check': [('readonly', True)], 'approved': [('readonly', True)], 'partial': [('readonly', True)]})
    location_id = fields.Many2one(
        'stock.location', "Source Location",
        default=lambda self: self.env['stock.picking.type'].browse(
            self._context.get('default_picking_type_id')).default_location_src_id,
        required=True,
        states={'to_check': [('readonly', True)], 'approved': [('readonly', True)], 'partial': [('readonly', True)]},tracking=True)
    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location",
        default=lambda self: self.env['stock.picking.type'].browse(
            self._context.get('default_picking_type_id')).default_location_dest_id,
        required=True,
        states={'to_check': [('readonly', True)], 'approved': [('readonly', True)], 'partial': [('readonly', True)]},tracking=True)
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        required=True,
        states={'to_check': [('readonly', True)], 'approved': [('readonly', True)], 'partial': [('readonly', True)]},tracking=True)
    user_id = fields.Many2one(
        'res.users', 'Request_by', default=lambda self: self.env.user, readonly=True, tracking=True)
    approved_id = fields.Many2one(
        'res.users', 'Approved_by', readonly=True, tracking=True)
    approved_date = fields.Datetime('Approved Date', readonly=True, tracking=True)
    received_id = fields.Many2one(
        'res.users', 'Received_by', readonly=True, tracking=True)
    received_date = fields.Datetime('Received Date', readonly=True, tracking=True)
    canceled_id = fields.Many2one(
        'res.users', 'Canceled_by', readonly=True, tracking=True)

    item_ids = fields.One2many('transfer.request.item', 'transfer_request_id', 'Items',
                               states={'to_check': [('readonly', True)], 'approved': [('readonly', True)], 'partial': [('readonly', True)]},tracking=True)
    stock_picking = fields.Many2one('stock.picking', 'Transfer', readonly=True, tracking=True)
    stock_picking_remaining_id = fields.Many2one('stock.picking', 'Remaining Transfer', readonly=True, tracking=True)

    purchase_request_id = fields.Many2one(
        'purchase.request',
        string='Purchase Request',
        copy=False,
        readonly=True,
    )

    has_unavailable_items = fields.Boolean(
        string='Has Unavailable Items',
        compute='_compute_has_unavailable_items',
        store=False,
    )

    user_can_edit = fields.Boolean(
        string='User Can Edit',
        compute='_compute_user_can_edit',
        store=False,
    )

    @api.depends('item_ids', 'item_ids.products_availability')
    def _compute_has_unavailable_items(self):
        for record in self:
            if record.state == 'partial':
                lines = record.item_ids.filtered(lambda l: not l.is_transferred)
            else:
                lines = record.item_ids
            record.has_unavailable_items = any(
                line.products_availability == 0 for line in lines
            )

    @api.depends('location_id')
    def _compute_user_can_edit(self):
        for record in self:
            # Check if user has access to source location
            allowed = getattr(record.env.user, "x_studio_locations", False)
            allowed_ids = allowed.ids if allowed else []
            record.user_can_edit = record.location_id.id in allowed_ids if allowed_ids and record.location_id else False

    # ---- Product Catalog Mixin Methods ----

    def _get_product_catalog_domain(self):
        return [('type', '=', 'product')]

    def _get_product_catalog_record_lines(self, product_ids):
        grouped_lines = defaultdict(lambda: self.env['transfer.request.item'])
        for line in self.item_ids:
            if line.product_id.id not in product_ids:
                continue
            grouped_lines[line.product_id] |= line
        return grouped_lines

    def _get_product_catalog_order_data(self, products, **kwargs):
        return {product.id: {'price': product.standard_price} for product in products}

    def _is_readonly(self):
        return self.state != 'draft'

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        line = self.item_ids.filtered(lambda l: l.product_id.id == product_id)
        if line:
            if quantity <= 0:
                line.unlink()
            else:
                line.demand = quantity
        elif quantity > 0:
            self.env['transfer.request.item'].create({
                'transfer_request_id': self.id,
                'product_id': product_id,
                'demand': quantity,
            })
        return 0

    def _find_receipt_picking_type(self, rec):
        PickingType = self.env['stock.picking.type']
        # Prefer same company, ordered by sequence then id
        pt = PickingType.search([
            ('code', '=', 'incoming'),
        ], order='sequence,id', limit=1)
        if pt:
            return pt
        # Fallback: a global (company-less) receipt type
        pt = PickingType.search([
            ('code', '=', 'incoming'),
        ], order='sequence,id', limit=1)
        if pt:
            return pt
        # Final fallback: any receipt type
        return PickingType.search([('code', '=', 'incoming')], order='sequence,id', limit=1)


    def action_create_purchase_request(self):
        """Create a Purchase Request (one per Transfer Request) from lines."""
        for rec in self:
            if rec.purchase_request_id:
                # Already created once — open it instead of duplicating
                action = rec.purchase_request_id.get_formview_action()
                return action

            if not rec.item_ids:
                raise UserError(_("No transfer lines to create purchase request."))

            available_lines = rec.item_ids.filtered(lambda l: l.products_availability > 0)
            unavailable_lines = rec.item_ids.filtered(lambda l: l.products_availability <= 0)

            if not unavailable_lines:
                raise UserError(_("All items are available in the source location. No purchase request needed."))

            # Warn if some items will be skipped because they already have stock
            if available_lines and not self.env.context.get('skip_warning'):
                msg = _(
                    "The following items already have stock available and will NOT be included in the purchase request:\n%s\n\n"
                    "Only the %d unavailable item(s) will be requested. Do you want to proceed?"
                ) % (
                    '\n'.join('- %s (available: %s)' % (l.product_id.display_name, l.products_availability) for l in available_lines),
                    len(unavailable_lines),
                )
                wizard = self.env['transfer.request.confirm.wizard'].create({
                    'transfer_request_id': rec.id,
                    'message': msg,
                    'action_type': 'purchase_request',
                })
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'transfer.request.confirm.wizard',
                    'res_id': wizard.id,
                    'view_mode': 'form',
                    'target': 'new',
                }

            # Collect PR lines from unavailable lines only
            pr_lines_vals = []
            for line in unavailable_lines:
                # Only include items with zero availability in source location
                if line.products_availability != 0:
                    continue

                # Adjust field names to your schema: product_id & demand are assumed
                product = line.product_id
                qty = line.demand
                if not product or not qty or qty <= 0:
                    continue

                pr_lines_vals.append((0, 0, {
                    'product_id': product.id,
                    'name': product.display_name,
                    'product_uom_id': product.uom_po_id.id or product.uom_id.id,
                    'product_qty': qty,
                    # optional: price/unit, analytic, date_required, etc.
                    # 'date_required': fields.Date.today(),
                }))

            if not pr_lines_vals:
                raise UserError(_("Nothing to request: all lines are empty or zero."))
            
            receipt_type = self._find_receipt_picking_type(rec)
            if not receipt_type:
                raise UserError(_("No 'Receipts' operation type (incoming) is configured."))

            vals = {
                'name': 'Request',
                'transfer_request_id': rec.id,   # reverse link on PR
                'request_line_ids': pr_lines_vals,
                'picking_type_id': receipt_type.id,
                'requested_by': self.env.user.id,  # Explicitly set required field
                # optional: requester, picking type, warehouse, notes…
            }
            _logger.info("Creating purchase request with vals: %s", vals)
            pr = self.env['purchase.request'].create(vals)
            _logger.info("Purchase request created: %s (name=%s)", pr.id, pr.name)

            rec.purchase_request_id = pr.id

            return pr.get_formview_action()
        
    def action_submit(self):
        for record in self:
            if record.location_id == record.location_dest_id:
                raise UserError(
                    "Source and destination location are the same. Please check and try again."
                )
            if not record.item_ids:
                raise UserError(_("Please add at least one item line before submitting."))
            allowed = getattr(self.env.user, "x_studio_locations", False)
            allowed_ids = allowed.ids if allowed else []
            if not allowed_ids or record.location_dest_id.id not in allowed_ids:
                raise UserError(
                    "Please check the destination of the transfer request. Your location doesn't match the destination.")
            record.state = "to_check"
            record.user_id = self.env.user.id

    def action_reset_to_draft(self):
        for record in self:
            record.state = "draft"

    def action_receive(self):
        for record in self:
            if self.env.user.x_studio_locations.ids != False and len(
                    self.env.user.x_studio_locations.ids) != 0 and record.location_dest_id.id in self.env.user.x_studio_locations.ids:
                record.state = "done"
                record.received_id = self.env.user.id
                record.received_date = fields.Datetime.now()
                picking = self.create_transfer()
                self.validate_transfer()
            else:
                raise UserError(
                    "Please check the destination id of transfer request. Your location Doesn't match with destination")

    def action_done(self):
        for record in self:
            record.write({'state': 'done'})

    def action_send_remaining(self):
        self.ensure_one()
        rec = self

        remaining = rec.item_ids.filtered(lambda l: l.product_id and not l.is_transferred)
        if not remaining:
            raise UserError(_("There are no remaining items to transfer."))

        skip_qty_check = rec.picking_type_id.allow_confirm_without_qty
        available = remaining.filtered(lambda l: (l.products_availability or 0.0) > 0)
        unavailable = remaining.filtered(lambda l: (l.products_availability or 0.0) <= 0)

        if unavailable and not skip_qty_check and not self.env.context.get('skip_warning'):
            if not available:
                raise UserError(_("None of the remaining items are available in the source location."))
            msg = _(
                "The following remaining items still have no stock and will be excluded:\n%s\n\n"
                "Only the %d available item(s) will be transferred. Do you want to proceed?"
            ) % (
                '\n'.join('- %s' % l.product_id.display_name for l in unavailable),
                len(available),
            )
            wizard = self.env['transfer.request.confirm.wizard'].create({
                'transfer_request_id': rec.id,
                'message': msg,
                'action_type': 'send_remaining',
            })
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'transfer.request.confirm.wizard',
                'res_id': wizard.id,
                'view_mode': 'form',
                'target': 'new',
            }

        rec.with_context(skip_warning=True, is_remaining_transfer=True).create_transfer()

        # Update state: if all items are now transferred → approved, else stay partial
        all_transferred = all(l.is_transferred for l in rec.item_ids.filtered('product_id'))
        rec.write({'state': 'approved' if all_transferred else 'partial'})

        return True

    def action_cancel(self):
        for record in self:
            if self.env.user.x_studio_locations.ids != False and len(
                    self.env.user.x_studio_locations.ids) != 0 and record.location_id.id in self.env.user.x_studio_locations.ids:
                record.state = "cancel"
                record.canceled_id = self.env.user.id
            else:
                raise UserError(
                    "Please check the destination id of transfer request. Your location Doesn't match with source")

    def action_confirm(self):
        for rec in self:
            # ---- Same location guard ----
            if rec.location_id == rec.location_dest_id:
                raise UserError(_("Source and destination location are the same. Please check and try again."))

            _logger.info("confirm ******************************************")
            _logger.info(rec.env.user.x_studio_locations.ids if hasattr(rec.env.user, "x_studio_locations") else [])
            _logger.info(rec.location_id.id)

            # ---- Permission: require user has allowed locations AND source is among them ----
            allowed = getattr(rec.env.user, "x_studio_locations", False)
            allowed_ids = allowed.ids if allowed else []
            if not allowed_ids or rec.location_id.id not in allowed_ids:
                raise UserError(_("Please check the source of the transfer request. Your location doesn't match the source."))

            # ---- Require at least one item line ----
            if not rec.item_ids:
                raise UserError(_("Please add at least one item line before confirming."))

            # ---- Validate item lines ----
            skip_qty_check = rec.picking_type_id.allow_confirm_without_qty
            for line in rec.item_ids:
                if line.demand is None:
                    raise UserError(_("Please enter demand for %s.") % (line.product_id.display_name or _("(no product)")))
                if line.demand < 0:
                    raise UserError(_("Demand is lower than 0 for %s.") % (line.product_id.display_name,))
                if line.product_id and not skip_qty_check:
                    avail = line.products_availability or 0.0
                    if avail > 0 and line.demand > avail:
                        raise UserError(_("Demand (%s) is higher than stock on hand (%s) for %s.")
                                        % (line.demand, avail, line.product_id.display_name))

            # ---- Warn if some items have no availability ----
            if not skip_qty_check and not self.env.context.get('skip_warning'):
                unavailable_lines = rec.item_ids.filtered(
                    lambda l: l.product_id and (l.products_availability or 0.0) <= 0
                )
                available_lines = rec.item_ids.filtered(
                    lambda l: l.product_id and (l.products_availability or 0.0) > 0
                )
                if unavailable_lines and available_lines:
                    msg = _(
                        "The following items have no stock available and will be EXCLUDED from the transfer:\n%s\n\n"
                        "Only the %d available item(s) will be transferred. Do you want to proceed?"
                    ) % (
                        '\n'.join('- %s' % l.product_id.display_name for l in unavailable_lines),
                        len(available_lines),
                    )
                    wizard = self.env['transfer.request.confirm.wizard'].create({
                        'transfer_request_id': rec.id,
                        'message': msg,
                        'action_type': 'confirm',
                    })
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'transfer.request.confirm.wizard',
                        'res_id': wizard.id,
                        'view_mode': 'form',
                        'target': 'new',
                    }
                elif unavailable_lines and not available_lines:
                    raise UserError(_("None of the items are available in the source location. Cannot confirm transfer."))

            # ---- If a picking exists and is draft, push planned quantities ----
            picking = getattr(rec, "stock_picking", False)
            if picking:
                _logger.info("TransferRequest %s has picking %s (state=%s)", rec.id, picking.display_name, picking.state)
                if picking.state != 'draft':
                    raise UserError(_("The related picking (%s) is not in draft. "
                                    "Set it to draft (or recreate) before applying quantities.") % (picking.display_name,))
                for line in rec.item_ids:
                    if not line.product_id:
                        continue
                    # Prefer adjusting planned qty on stock.moves in draft
                    moves = picking.move_ids_without_package.filtered(lambda m: m.product_id == line.product_id)
                    if moves:
                        for mv in moves:
                            _logger.info("Updating move %s for %s: %s -> %s",
                                        mv.id, line.product_id.display_name, mv.product_uom_qty, line.demand)
                            mv.product_uom_qty = line.demand
                    else:
                        # Fallback to move lines if your flow uses them in draft
                        updated = False
                        for ml in picking.move_line_ids:
                            if ml.product_id == line.product_id:
                                _logger.info("Updating move line %s for %s: %s -> %s",
                                            ml.id, line.product_id.display_name, ml.product_uom_qty, line.demand)
                                ml.product_uom_qty = line.demand
                                updated = True
                                break
                        if not updated:
                            _logger.warning("No move/move line found in picking %s for product %s; "
                                            "consider creating a draft move.", picking.display_name, line.product_id.display_name)

            # ---- Approve & stamp approver ----
            has_skipped = self.env.context.get('skip_warning') and rec.item_ids.filtered(
                lambda l: l.product_id and (l.products_availability or 0.0) <= 0
            )
            new_state = 'partial' if has_skipped else 'approved'
            rec.write({
                'state': new_state,
                'approved_id': rec.env.user.id,
                'approved_date': fields.Datetime.now(),
            })

            # ---- Create the stock transfer (ready, not validated) ----
            if not rec.stock_picking:
                rec.create_transfer()

        return True
    
    # def action_confirm(self):
    #     for record in self:
    #         if record.location_id.id != record.location_dest_id.id:
    #             _logger.info("confirm ******************************************")
    #             _logger.info(self.env.user.x_studio_locations.ids)
    #             _logger.info(record.location_id.id)
    #             if self.env.user.x_studio_locations.ids != False and len(
    #                     self.env.user.x_studio_locations.ids) != 0 and record.location_id.id in self.env.user.x_studio_locations.ids:
    #                 record.state = 'approved'
    #                 record.approved_id = self.env.user.id 
    #             else:
    #                 raise UserError(
    #                     "Please check the destination id of transfer request. Your location Doesn't match with source")

    #         else:
    #             raise UserError("source and destination location are the same. Please Check and try again")

    def action_print(self):
        """Print the transfer request report"""
        return self.env.ref('store_request.action_report_transfer_request').report_action(self)

    @api.model
    def create(self, vals):
        res = super(Transfer_request_double, self).create(vals)
        name = self.env['ir.sequence'].next_by_code('transfer.request')
        res.write({'name': name})
        return res

    @api.onchange('picking_type_id')
    def onchange_picking_type(self):
        if self.picking_type_id:
            if self.picking_type_id.default_location_src_id:
                location_id = self.picking_type_id.default_location_src_id.id
            else:
                customerloc, location_id = self.env['stock.warehouse']._get_partner_locations()

            if self.picking_type_id.default_location_dest_id:
                location_dest_id = self.picking_type_id.default_location_dest_id.id
            else:
                location_dest_id, supplierloc = self.env['stock.warehouse']._get_partner_locations()

            self.location_id = location_id
            self.location_dest_id = location_dest_id

    @api.onchange('location_id')
    def _compute_availability_of_products(self):
        for record in self:
            _logger.info("1ocation*****************************************")
            for line in record.item_ids:
                if len(record.location_id) != 0:
                    stock_quant = self.env['stock.quant'].sudo().search(
                        [("location_id", "=", record.location_id.id), ("product_id", "=", line.product_id.id)])
                    for quant in stock_quant:
                        line.products_availability += quant.quantity
                        # line.products_availability+=10
                        # record.products_availability_dest -= quant.reserved_quantity
                    if line.products_availability < 0:
                        line.products_availability = 0
                    if line.demand > line.products_availability:
                        line.demand = 0
                        # raise UserError("Demand is higher than stock on hand")
                    if line.products_availability == 0:
                        line.demand = 0
                        # raise UserError("This Product is not available in the source location")

    @api.onchange('location_dest_id')
    def _compute_availability_of_products(self):
        for record in self:
            _logger.info("1ocation*****************************************")
            for line in record.item_ids:
                if len(record.location_dest_id) != 0:
                    stock_quant = self.env['stock.quant'].sudo().search(
                        [("location_id", "=", record.location_dest_id.id), ("product_id", "=", line.product_id.id)])
                    for quant in stock_quant:
                        line.products_availability_dest += quant.quantity
                        # record.products_availability_dest -= quant.reserved_quantity
                    if line.products_availability_dest < 0:
                        line.products_availability_dest = 0
                    if line.demand > line.products_availability_dest:
                        line.demand = 0
                        # raise UserError("Demand is higher than stock on hand")
                    if line.products_availability_dest == 0:
                        line.demand = 0
                        # raise UserError("This Product is not available in the source location")

    @api.onchange('item_ids')
    def _compute_sequence_for_items(self):
        for record in self:
            _logger.info("compute number*****************************************")
           
            for index, line in enumerate(record.item_ids, start=1):
                line.number = index
                print("print----------->")
                if line.products_availability < 0:
                    line.products_availability = 0
                    line.demand = 0                   
                    print("12345")
                if line.products_availability_dest < 0:
                    line.products_availability_dest = 0
                    line.demand = 0
                # print("sequence item")
                print(line.products_availability ,line.products_availability_dest)

    

    def create_transfer(self):
        try:
            for record in self:
                vals = {
                    "scheduled_date": record.scheduled_date,
                    "date": record.date,
                    "picking_type_id": record.picking_type_id.id,
                    "location_id": record.location_id.id,
                    "location_dest_id": record.location_dest_id.id,
                    "user_id": record.write_uid.id,
                    "origin": record.name
                }
                move_ids = []
                skip_unavailable = self.env.context.get('skip_warning')
                transferred_lines = []
                for line in record.item_ids:
                    if line.product_id and line.demand > 0:
                        if skip_unavailable and (line.products_availability or 0.0) <= 0:
                            continue
                        move_data = {
                            "name": line.product_id.display_name,
                            "product_id": line.product_id.id,
                            "product_uom_qty": line.demand,
                            "product_uom": line.product_id.uom_id.id,
                            "location_id": record.location_id.id,
                            "location_dest_id": record.location_dest_id.id,
                        }
                        move_ids.append((0, 0, move_data))
                        transferred_lines.append(line)

                vals['move_ids_without_package'] = move_ids
                is_remaining = self.env.context.get('is_remaining_transfer')
                stock_picking = self.env['stock.picking'].sudo().with_context(skip_check_company=True).create(vals)
                _logger.info("Created picking %s for transfer request %s", stock_picking.name, record.name)
                if is_remaining:
                    record.sudo().stock_picking_remaining_id = stock_picking.id
                else:
                    record.sudo().stock_picking = stock_picking.id

                # Confirm and assign to reach "Ready" state
                stock_picking.action_confirm()
                stock_picking.action_assign()

                # Mark included lines as transferred
                for line in transferred_lines:
                    line.sudo().write({'is_transferred': True})

                return record
        except Exception as e:
            _logger.info(e)
            raise UserError("Creation of Transfer Has Failed")

    def validate_transfer(self):
        # try:
        stock_picking = self.stock_picking
        for each_stock_move in stock_picking.move_ids_without_package:
            found_list = [line for line in self.item_ids if line.product_id == each_stock_move.product_id]
            if len(found_list) == 1:
                if found_list[0].products_availability < found_list[0].received and found_list[0].received != 0:
                    raise UserError("Please remove or lower the received quantity of product -  " + found_list[
                        0].product_id.name + " as there are less products available")
                if found_list[0].received != each_stock_move.product_uom_qty and found_list[0].available_in_store == True:
                    each_stock_move.product_uom_qty = found_list[0].received
                if found_list[0].available_in_store == False or found_list[0].received == 0:
                            each_stock_move.unlink()
            else:
                if len(found_list) == 0:
                    each_stock_move.unlink()
                elif len(found_list) > 1:
                    raise UserError(
                        "There are more than one similar items for this request so please remove them from the main transfer and then remove them on this transfer request")

        # Confirm and validate the transfer
        if stock_picking.state != 'done':
            # Step 1: Confirm the picking to create stock moves
            stock_picking.action_confirm()

            # Step 2: Reserve quantities (check availability)
            stock_picking.action_assign()

            # Step 3: Set quantity on move lines based on transfer request items
            for move_line in stock_picking.move_line_ids_without_package:
                # Find the corresponding transfer request item
                found_list = [line for line in self.item_ids if line.product_id == move_line.product_id and line.available_in_store and line.received > 0]
                if len(found_list) == 1:
                    received_qty = found_list[0].received
                    # Set quantity on the move line
                    move_line.quantity = received_qty

            # Step 4: Validate the transfer
            stock_picking.button_validate()

        return True

   

class Transfer_request_item_double(models.Model):
    _name = "transfer.request.item"
    _description = "Transfer Request item"

    number = fields.Integer('Number', compute='_compute_number', store=True, readonly=True)
    transfer_request_id = fields.Many2one('transfer.request', 'Request')
    product_id = fields.Many2one('product.product', 'Product')
    products_availability = fields.Float(
        string="Product Availability", compute='_compute_products_availability')
    products_availability_dest = fields.Float(
        string="Product Availability Destination", compute='_compute_products_availability')
    demand = fields.Float(string="Demand")
    sent = fields.Float(string="Sent", default=0.0)
    received = fields.Float(string="Received", default=0.0)

    available_in_store = fields.Boolean("Available", default=True, readonly=True)
    is_transferred = fields.Boolean("Transferred", default=False, readonly=True)

    lot_ids = fields.One2many('transfer.request.item.lot', 'transfer_request_item_id', 'Lots/Serials')
    tracking = fields.Selection(related='product_id.tracking', string='Tracking', readonly=True)
    use_lots = fields.Boolean(compute='_compute_use_lots', string='Use Lots/Serials')

    user_can_receive = fields.Boolean(
        string='User Can Receive',
        compute='_compute_user_can_receive',
        store=False,
    )

    user_can_send = fields.Boolean(
        string='User Can Send',
        compute='_compute_user_can_send',
        store=False,
    )

    @api.depends('transfer_request_id.item_ids')
    def _compute_number(self):
        for record in self:
            if record.transfer_request_id:
                for index, line in enumerate(record.transfer_request_id.item_ids, start=1):
                    line.number = index
            else:
                record.number = 0

    @api.depends('transfer_request_id.location_dest_id')
    def _compute_user_can_receive(self):
        for record in self:
            # Check if user has access to destination location
            if record.transfer_request_id and record.transfer_request_id.location_dest_id:
                allowed = getattr(record.env.user, "x_studio_locations", False)
                allowed_ids = allowed.ids if allowed else []
                record.user_can_receive = record.transfer_request_id.location_dest_id.id in allowed_ids if allowed_ids else False
            else:
                record.user_can_receive = False

    @api.depends('transfer_request_id.location_id')
    def _compute_user_can_send(self):
        for record in self:
            # Check if user has access to source location
            if record.transfer_request_id and record.transfer_request_id.location_id:
                allowed = getattr(record.env.user, "x_studio_locations", False)
                allowed_ids = allowed.ids if allowed else []
                record.user_can_send = record.transfer_request_id.location_id.id in allowed_ids if allowed_ids else False
            else:
                record.user_can_send = False

    def action_add_from_catalog(self):
        order = self.env['transfer.request'].browse(self.env.context.get('order_id'))
        return order.action_add_from_catalog()

    def _get_product_catalog_lines_data(self, **kwargs):
        if len(self) == 1:
            return {
                'quantity': self.demand,
                'price': self.product_id.standard_price,
                'readOnly': self.transfer_request_id._is_readonly(),
            }
        elif self:
            self.product_id.ensure_one()
            return {
                'quantity': sum(self.mapped('demand')),
                'readOnly': True,
            }
        return {'quantity': 0}

    @api.constrains('received', 'sent', 'demand')
    def _check_received_quantity(self):
        for record in self:
            if record.received < 0:
                raise UserError(_("Received quantity cannot be negative for %s.") % record.product_id.display_name)
            if record.sent < 0:
                raise UserError(_("Sent quantity cannot be negative for %s.") % record.product_id.display_name)
            if record.received > record.demand:
                raise UserError(_("Received quantity (%s) cannot be greater than demand (%s) for %s.")
                    % (record.received, record.demand, record.product_id.display_name))
            if record.sent > record.demand:
                raise UserError(_("Sent quantity (%s) cannot be greater than demand (%s) for %s.")
                    % (record.sent, record.demand, record.product_id.display_name))
            if record.received > record.sent:
                raise UserError(_("Received quantity (%s) cannot be greater than sent quantity (%s) for %s.")
                    % (record.received, record.sent, record.product_id.display_name))

    @api.model
    def create(self, vals):
        _logger.info("******************************************create")

        for record in self:
            _logger.info(record.product_id)
            if len(record.product_id) != 0 and (record.transfer_request_id == False or len(record.transfer_request_id.location_id) != 0):
                raise UserError("Please Check source Location Before Creating Request Item")
            for each_item in record.transfer_request_id.item_ids:
                if each_item.product_id == record.product_id:
                    raise UserError("Product Already Exsists In the List")
            if record.transfer_request_id != "draft":
                raise UserError(
                    "Only transfer requests that are in draft state are allowed to increase the number of items.")
            # vals["number"] = len(record.transfer_request_id.item_ids)
        res = super(Transfer_request_item_double,self).create(vals)
        return res

    def unlink(self):
        """Prevent deletion of items when transfer request is not in draft state"""
        for record in self:
            if record.transfer_request_id and record.transfer_request_id.state != 'draft':
                raise UserError(_(
                    "You cannot delete items when the transfer request is not in draft state. "
                    "Current state: %s") % dict(record.transfer_request_id._fields['state'].selection).get(record.transfer_request_id.state)
                )
        return super(Transfer_request_item_double, self).unlink()

    @api.depends('transfer_request_id', 'transfer_request_id.location_id', 'transfer_request_id.location_dest_id', 'product_id')
    def _compute_products_availability(self):
        for record in self:
            record.products_availability = 0
            record.products_availability_dest = 0
            if not record.product_id:
                continue
            if record.transfer_request_id.location_id:
                record.products_availability = record.product_id.with_context(
                    location=record.transfer_request_id.location_id.id
                ).qty_available
            if record.transfer_request_id.location_dest_id:
                record.products_availability_dest = record.product_id.with_context(
                    location=record.transfer_request_id.location_dest_id.id
                ).qty_available

    # @api.onchange('demand')
    # def _compute_demand_is_available(self):
    #     for record in self:
    #         _logger.info("*****************************************demand")
    #         _logger.info(record.product_id)
    #         if record.demand < 0:
    #             record.demand = 0
    #             raise UserError("Demand is lower than 0")
    #         if len(record.product_id) != 0 and record.demand > record.products_availability:
    #             record.demand = 0
    #             raise UserError("Demand is higher than stock on hand")
    #         if len(record.product_id) != 0 and record.products_availability == 0:
    #             record.demand = 0
    #             raise UserError("This Product is not available in the source location")
    #         _logger.info("here inside change transfer top")
    #         _logger.info(record.transfer_request_id)
    #         _logger.info(record.transfer_request_id.state)
    #         _logger.info(record.transfer_request_id.stock_picking)
    #         _logger.info(record.transfer_request_id.stock_picking.state)
    #         if record.transfer_request_id.stock_picking != False and (
    #                 record.transfer_request_id.stock_picking.state == 'draft' and (
    #                 record.transfer_request_id.state == 'waiting' or record.transfer_request_id.state == 'draft')):
    #             _logger.info("here inside change transfer big one")
    #             for lines in record.transfer_request_id.stock_picking.move_line_ids:
    #                 _logger.info("looping")
    #                 if lines.product_id == record.product_id:
    #                     lines.product_uom_qty = record.demand
    #                     _logger.info("change transfer lines *******************")
    #                     break

    def action_change_availability(self):
        for record in self:
            if record.available_in_store == True:
                if record.transfer_request_id.stock_picking != False and (
                        record.transfer_request_id.stock_picking.state == 'draft' and (
                        record.transfer_request_id.state == 'waiting' or record.transfer_request_id.state == 'draft')):
                    for lines in record.transfer_request_id.stock_picking.move_ids_without_package:
                        if lines.product_id.id == record.product_id.id:
                            lines.product_uom_qty = 0
                            lines.quantity_done = 0
            else:
                if record.transfer_request_id.stock_picking != False and (
                        record.transfer_request_id.stock_picking.state == 'draft' and (
                        record.transfer_request_id.state == 'waiting' or record.transfer_request_id.state == 'draft')):
                    for lines in record.transfer_request_id.stock_picking.move_ids_without_package:
                        if lines.product_id.id == record.product_id.id:
                            lines.product_uom_qty = record.demand
                            # lines.quantity_done = 0
            record.available_in_store = not record.available_in_store


class Transfer_request_item_lot(models.Model):
    _name = "transfer.request.item.lot"
    _description = "Transfer Request Item Lot/Serial"

    transfer_request_item_id = fields.Many2one('transfer.request.item', 'Transfer Item', required=True, ondelete='cascade')
    lot_id = fields.Many2one('stock.lot', 'Lot/Serial Number', required=True, domain="[('product_id', '=', product_id)]")
    product_id = fields.Many2one('product.product', related='transfer_request_item_id.product_id', string='Product', store=True, readonly=True)
    quantity = fields.Float('Quantity', default=1.0, required=True)

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise UserError(_("Quantity must be greater than 0 for lot/serial %s.") % record.lot_id.name)


class ResUsers(models.Model):
    _inherit = 'res.users'
    x_studio_locations = fields.Many2many('stock.location', string='Locations')
