from odoo import api, fields, models
from odoo.exceptions import UserError


class DualOrder(models.Model):
    _name = 'dual.order'
    _description = 'Dual Order - Service & Storable Product Splitter'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Order Reference",
                       default=lambda self: self.env['ir.sequence'].next_by_code('dual.order'))
    partner_id = fields.Many2one('res.partner', string="Customer", required=True)
    order_line_ids = fields.One2many('dual.order.line', 'order_id', string="Order Lines")

    sale_order_id = fields.Many2one('sale.order', string="Related Sales Order", readonly=True)
    picking_id = fields.Many2one('stock.picking', string="Related Delivery Order", readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], default='draft')

    def action_confirm(self):
        SaleOrder = self.env['sale.order']
        StockPicking = self.env['stock.picking']
        StockMove = self.env['stock.move']

        service_lines = self.order_line_ids.filtered(lambda l: l.product_id.type == 'service')
        storable_lines = self.order_line_ids.filtered(lambda l: l.product_id.type == 'product')

        if not service_lines and not storable_lines:
            raise UserError("You must add at least one service or storable product line.")

        if service_lines:
            sale_order = SaleOrder.create({
                'partner_id': self.partner_id.id,
                'origin': self.name,
                'order_line': [(0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': line.price_unit,
                }) for line in service_lines],
            })
            self.sale_order_id = sale_order.id
            sale_order.action_confirm()

        if storable_lines:
            picking_type = self.env.ref('stock.picking_type_out')
            picking = StockPicking.create({
                'partner_id': self.partner_id.id,
                'picking_type_id': picking_type.id,
                'origin': self.name,
            })
            for line in storable_lines:
                StockMove.create({
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_id.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                })
            self.picking_id = picking.id

        self.state = 'confirmed'
        return True

    # Smart Button Actions
    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError("No related Sales Order.")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
            'target': 'current',
        }

    def action_view_picking(self):
        self.ensure_one()
        if not self.picking_id:
            raise UserError("No related Delivery Order.")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.picking_id.id,
            'target': 'current',
        }


class DualOrderLine(models.Model):
    _name = 'dual.order.line'
    _description = 'Dual Order Line'

    order_id = fields.Many2one('dual.order', string="Order Reference",  ondelete='cascade')
    product_id = fields.Many2one('product.product', string="Product", required=True)
    product_uom_qty = fields.Float(string="Quantity", default=1.0)
    price_unit = fields.Float(string="Unit Price")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.list_price
