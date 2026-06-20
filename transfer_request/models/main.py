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

class Transfer_request_double(models.Model):
    _name = "transfer.request"
    _description = "Transfer Request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(
        'Reference', default='/',
        copy=False, index=True, readonly=True)
    note = fields.Text('Notes', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting For Approval'),
        ('approved', 'Approve'),
        ('done', 'Received'),
        ('cancel', 'Cancel')
    ], string='Status',
        copy=False, index=True, readonly=True, store=True, tracking=True, default="draft")
    
    date = fields.Datetime(
        'Creation Date',
        default=fields.Datetime.now, index=True, tracking=True,
        help="Creation Date, usually the time of the order",
        states={'approved': [('readonly', True)], 'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    
    scheduled_date = fields.Datetime('Scheduled date', default=fields.Datetime.now, copy=False,
                                     help="Date at which the transfer has been processed or cancelled.",
                                     states={'approved': [('readonly', True)], 'done': [('readonly', True)],
                                             'cancel': [('readonly', True)]})
    
    location_id = fields.Many2one(
        'stock.location', "Source Location",
        default=lambda self: self.env['stock.picking.type'].browse(
            self._context.get('default_picking_type_id')).default_location_src_id,
        required=True,
        states={'approved': [('readonly', True)], 'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        tracking=True)
    
    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location",
        default=lambda self: self.env['stock.picking.type'].browse(
            self._context.get('default_picking_type_id')).default_location_dest_id,
        required=True,
        tracking=True,
        states={'approved': [('readonly', True)], 'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        required=True,
        tracking=True,
        states={'approved': [('readonly', True)], 'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    
    user_id = fields.Many2one(
        'res.users', 'Request_by', default=lambda self: self.env.user, readonly=True, tracking=True)
    approved_id = fields.Many2one(
        'res.users', 'Approved_by', readonly=True, tracking=True)
    received_id = fields.Many2one(
        'res.users', 'Received_by', readonly=True, tracking=True)
    canceled_id = fields.Many2one(
        'res.users', 'Canceled_by', readonly=True, tracking=True)
    
    item_ids = fields.One2many('transfer.request.item', 'transfer_request_id', 'Items',
                               tracking=True,
                               states={'approved': [('readonly', True)], 'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    
    stock_picking = fields.Many2one('stock.picking', 'Transfer', readonly=True, tracking=True)
    stock_picking_receive = fields.Many2one('stock.picking', 'Receive Transfer', readonly=True, tracking=True)

    def _check_user_location_access(self, location_id, action_type):
        """Check if user has access to the location for specific action"""
        user_locations = self.env.user.x_studio_locations.ids
        
        if not user_locations:
            raise UserError(f"You don't have any assigned locations. Please contact administrator.")
        
        if location_id not in user_locations:
            location_name = self.env['stock.location'].browse(location_id).name
            raise UserError(f"You don't have access to location '{location_name}' for {action_type}.")
        
        return True

    def action_request(self):
        for record in self:
            # Check if source and destination are different
            if record.location_id.id == record.location_dest_id.id:
                raise UserError("Source and destination location are the same. Please check and try again.")
            
            # Check if user has access to destination location (for requesting)
            self._check_user_location_access(record.location_dest_id.id, "requesting transfer")
            
            record.state = "waiting"
            record.user_id = self.env.user.id

    def action_receive(self):
        for record in self:
            # Check if user has access to destination location (for receiving)
            self._check_user_location_access(record.location_dest_id.id, "receiving transfer")

            # Validate the RECEIVE picking (Transit → Destination) - Stock arrives at destination
            picking_receive = record.stock_picking_receive.sudo()
            if picking_receive and picking_receive.state != 'done':
                # Confirm the receive picking first
                if picking_receive.state == 'draft':
                    picking_receive.action_confirm()

                # Check availability (stock should be in transit now)
                picking_receive.action_assign()

                # Set quantity for all move lines
                for move_line in picking_receive.move_line_ids_without_package:
                    if not move_line.quantity:
                        move_line.quantity = move_line.quantity_product_uom
                    _logger.info(f"RECEIVE - Setting quantity for {move_line.product_id.name}: {move_line.quantity}")

                # Validate it - Stock will arrive at destination
                picking_receive.button_validate()
                _logger.info("****** RECEIVE Picking Validated - Stock arrived at destination ******")

            record.state = "done"
            record.received_id = self.env.user.id

    def action_cancel(self):
        for record in self:
            # Check if user has access to source location (for canceling)
            self._check_user_location_access(record.location_id.id, "canceling transfer")
            
            record.state = "cancel"
            record.canceled_id = self.env.user.id

    def action_confirm(self):
        for record in self:
            if record.location_id.id == record.location_dest_id.id:
                raise UserError("Source and destination location are the same. Please check and try again.")
            
            _logger.info("confirm ******************************************")
            _logger.info(self.env.user.x_studio_locations.ids)
            _logger.info(record.location_id.id)
            
            # Check if user has access to source location (for confirming/approving)
            self._check_user_location_access(record.location_id.id, "approving transfer")
            
            record.state = 'approved'
            record.approved_id = self.env.user.id
            picking = self.create_transfer()
            self.validate_transfer()

    def action_print(self):
        for record in self:
            _logger.info("*************************************print")
            _logger.info(record.stock_picking)
            if record.stock_picking:
                _logger.info("***********************in picking")
                return self.env.ref('stock.action_report_picking').report_action(record.stock_picking)

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
    def _compute_availability_of_products_src(self):
        for record in self:
            _logger.info("location source onchange *****************************************")
            for line in record.item_ids:
                if record.location_id:
                    stock_quant = self.env['stock.quant'].sudo().search(
                        [("location_id", "=", record.location_id.id), ("product_id", "=", line.product_id.id)])
                    line.products_availability = 0
                    for quant in stock_quant:
                        line.products_availability += quant.quantity
                    
                    if line.products_availability < 0:
                        line.products_availability = 0
                    if line.demand > line.products_availability:
                        line.demand = 0
                    if line.products_availability == 0:
                        line.demand = 0

    @api.onchange('location_dest_id')
    def _compute_availability_of_products_dest(self):
        for record in self:
            _logger.info("location destination onchange *****************************************")
            for line in record.item_ids:
                if record.location_dest_id:
                    stock_quant = self.env['stock.quant'].sudo().search(
                        [("location_id", "=", record.location_dest_id.id), ("product_id", "=", line.product_id.id)])
                    line.products_availability_dest = 0
                    for quant in stock_quant:
                        line.products_availability_dest += quant.quantity
                    
                    if line.products_availability_dest < 0:
                        line.products_availability_dest = 0

    @api.onchange('item_ids')
    def _compute_sequence_for_items(self):
        for record in self:
            _logger.info("compute number*****************************************")
            for index, line in enumerate(record.item_ids):
                line.number = index
                print("print----------->")
                if line.products_availability < 0:
                    line.products_availability = 0
                    line.demand = 0                   
                    print("12345")
                if line.products_availability_dest < 0:
                    line.products_availability_dest = 0
                    line.demand = 0
                print(line.products_availability, line.products_availability_dest)

    def create_transfer(self):
        try:
            for record in self:
                # Get or create transit location
                transit_location = self.env['stock.location'].sudo().search([
                    ('usage', '=', 'transit'),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)

                if not transit_location:
                    transit_location = self.env['stock.location'].sudo().create({
                        'name': 'Transit Location',
                        'usage': 'transit',
                        'company_id': self.env.company.id,
                    })

                # Create first picking: Source → Transit (for sending)
                vals_send = {
                    "scheduled_date": record.scheduled_date,
                    "date": record.date,
                    "picking_type_id": record.picking_type_id.id,
                    "location_id": record.location_id.id,
                    "location_dest_id": transit_location.id,  # Send to transit
                    "user_id": record.write_uid.id,
                    "origin": record.name + " - Send"
                }
                move_ids = []
                _logger.info("******Creating Send Picking**********************")
                for line in record.item_ids:
                    if line.available_in_store:
                        move_data = {
                            "name": line.product_id.name,
                            "product_id": line.product_id.id,
                            "product_uom_qty": line.demand,
                            "product_uom": line.product_id.uom_id.id,
                            "location_id": record.location_id.id,
                            "location_dest_id": transit_location.id,
                        }
                        move_ids.append((0, 0, move_data))

                vals_send['move_ids_without_package'] = move_ids
                stock_picking_send = self.env['stock.picking'].sudo().create(vals_send)
                record.stock_picking = stock_picking_send.id

                # Create second picking: Transit → Destination (for receiving)
                vals_receive = {
                    "scheduled_date": record.scheduled_date,
                    "date": record.date,
                    "picking_type_id": record.picking_type_id.id,
                    "location_id": transit_location.id,  # From transit
                    "location_dest_id": record.location_dest_id.id,
                    "user_id": record.write_uid.id,
                    "origin": record.name + " - Receive"
                }
                move_ids_receive = []
                _logger.info("******Creating Receive Picking**********************")
                for line in record.item_ids:
                    if line.available_in_store:
                        move_data = {
                            "name": line.product_id.name,
                            "product_id": line.product_id.id,
                            "product_uom_qty": line.demand,
                            "product_uom": line.product_id.uom_id.id,
                            "location_id": transit_location.id,
                            "location_dest_id": record.location_dest_id.id,
                        }
                        move_ids_receive.append((0, 0, move_data))

                vals_receive['move_ids_without_package'] = move_ids_receive
                stock_picking_receive = self.env['stock.picking'].sudo().create(vals_receive)
                record.stock_picking_receive = stock_picking_receive.id

                return record
        except Exception as e:
            _logger.info(e)
            raise UserError("Creation of Transfer Has Failed")

    def validate_transfer(self):
        """Validate the SEND picking (Source → Transit) - Stock leaves source"""
        # stock_picking = self.stock_picking.sudo()
        stock_picking = self.stock_picking

        for each_stock_move in stock_picking.move_ids_without_package:
            found_list = [line for line in self.item_ids if line.product_id == each_stock_move.product_id]
            if len(found_list) == 1:
                if found_list[0].products_availability < found_list[0].demand and found_list[0].demand != 0:
                    raise UserError("Please remove or lower a demand of product -  " + found_list[
                        0].product_id.name + " as there are less products available")
                if found_list[0].demand != each_stock_move.product_uom_qty and found_list[0].available_in_store:
                    each_stock_move.product_uom_qty = found_list[0].demand
                if not found_list[0].available_in_store:
                    each_stock_move.unlink()
            else:
                if len(found_list) == 0:
                    each_stock_move.unlink()
                elif len(found_list) > 1:
                    raise UserError(
                        "There are more than one similar items for this request so please remove them from the main transfer and then remove them on this transfer request")

        # Validate the SEND picking - Stock will leave source and go to transit
        if stock_picking.state == 'draft':
            stock_picking.action_confirm()

        if stock_picking.state != 'done':
            # Check availability and reserve stock
            stock_picking.action_assign()

            # Set quantity for all move lines
            for move_line in stock_picking.move_line_ids_without_package:
                if not move_line.quantity:
                    move_line.quantity = move_line.quantity_product_uom
                _logger.info(f"SEND - Setting quantity for {move_line.product_id.name}: {move_line.quantity}")

            # Now validate the picking
            stock_picking.button_validate()
            _logger.info("****** SEND Picking Validated - Stock left source ******")

        return True


class Transfer_request_item_double(models.Model):
    _name = "transfer.request.item"
    _description = "Transfer Request item"
    
    number = fields.Integer('Number', default=0, readonly=True)
    transfer_request_id = fields.Many2one('transfer.request', 'Request')
    product_id = fields.Many2one('product.product', 'Product')
    products_availability = fields.Float(
        string="Product Availability", compute='_compute_products_availability')
    products_availability_dest = fields.Float(
        string="Product Availability Destination", compute='_compute_products_availability')
    demand = fields.Float(string="Demand")
    available_in_store = fields.Boolean("Available", default=True, readonly=True)

    @api.model
    def create(self, vals):
        _logger.info("******************************************create")
        res = super(Transfer_request_item_double, self).create(vals)
        
        # Check after creation
        if res.product_id and not res.transfer_request_id.location_id:
            raise UserError("Please check source location before creating request item")
        
        # Check for duplicate products
        existing_items = res.transfer_request_id.item_ids.filtered(lambda x: x.product_id == res.product_id and x.id != res.id)
        if existing_items:
            raise UserError("Product already exists in the list")
        
        if res.transfer_request_id.state != "draft":
            raise UserError("Only transfer requests that are in draft state are allowed to add items.")
        
        return res

    @api.depends('transfer_request_id', 'product_id')
    def _compute_products_availability(self):
        for record in self:
            _logger.info("*****************************************product availability")
            _logger.info(record.transfer_request_id.location_id)
            
            if record.transfer_request_id.location_id and record.transfer_request_id.location_dest_id and record.product_id:
                # Source location availability
                stock_quant = self.env['stock.quant'].sudo().search(
                    [("location_id", "=", record.transfer_request_id.location_id.id),
                     ("product_id", "=", record.product_id.id)])
                
                # Destination location availability
                stock_quant_dest = self.env['stock.quant'].sudo().search(
                    [("location_id", "=", record.transfer_request_id.location_dest_id.id),
                     ("product_id", "=", record.product_id.id)])
                
                _logger.info("*****************************************product numbers.....")
                record.products_availability = 0
                record.products_availability_dest = 0
                
                for quant in stock_quant:
                    record.products_availability += quant.quantity
                    record.products_availability -= quant.reserved_quantity
                
                for quant in stock_quant_dest:
                    record.products_availability_dest += quant.quantity
                    record.products_availability_dest -= quant.reserved_quantity
                  
                print(record.products_availability, record.products_availability_dest)
                print("available")
            else:
                record.products_availability = 0
                record.products_availability_dest = 0

    @api.onchange('demand')
    def _compute_demand_is_available(self):
        for record in self:
            _logger.info("*****************************************demand")
            _logger.info(record.product_id)
            
            if record.demand < 0:
                record.demand = 0
                raise UserError("Demand cannot be negative")
            
            if record.product_id and record.demand > record.products_availability:
                record.demand = 0
                raise UserError("Demand is higher than stock on hand")
            
            if record.product_id and record.products_availability == 0:
                record.demand = 0
                raise UserError("This product is not available in the source location")
            
            _logger.info("here inside change transfer top")
            _logger.info(record.transfer_request_id)
            _logger.info(record.transfer_request_id.state)
            _logger.info(record.transfer_request_id.stock_picking)
            
            if (record.transfer_request_id.stock_picking and 
                record.transfer_request_id.stock_picking.state == 'draft' and 
                record.transfer_request_id.state in ['waiting', 'draft']):
                
                _logger.info("here inside change transfer big one")
                for lines in record.transfer_request_id.stock_picking.move_line_ids:
                    _logger.info("looping")
                    if lines.product_id == record.product_id:
                        lines.product_uom_qty = record.demand
                        _logger.info("change transfer lines *******************")
                        break

    def action_change_availability(self):
        for record in self:
            if record.available_in_store:
                if (record.transfer_request_id.stock_picking and 
                    record.transfer_request_id.stock_picking.state == 'draft' and 
                    record.transfer_request_id.state in ['waiting', 'draft']):
                    
                    for lines in record.transfer_request_id.stock_picking.move_ids_without_package:
                        if lines.product_id.id == record.product_id.id:
                            lines.product_uom_qty = 0
                            lines.quantity_done = 0
            else:
                if (record.transfer_request_id.stock_picking and 
                    record.transfer_request_id.stock_picking.state == 'draft' and 
                    record.transfer_request_id.state in ['waiting', 'draft']):
                    
                    for lines in record.transfer_request_id.stock_picking.move_ids_without_package:
                        if lines.product_id.id == record.product_id.id:
                            lines.product_uom_qty = record.demand
            
            record.available_in_store = not record.available_in_store


class ResUsers(models.Model):
    _inherit = 'res.users'
    x_studio_locations = fields.Many2many('stock.location', string='Locations')