# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockMovementValuation(models.TransientModel):
    """Transient model to display stock movement valuation details."""
    _name = 'stock.movement.valuation'
    _description = 'Stock Movement Valuation Line'
    _order = 'date, id'

    wizard_id = fields.Many2one(
        'stock.snapshot.wizard',
        string='Snapshot Wizard',
        ondelete='cascade'
    )
    movement_wizard_id = fields.Many2one(
        'stock.movement.wizard',
        string='Movement Wizard',
        ondelete='cascade'
    )
    date = fields.Datetime(string='Date')
    reference = fields.Char(string='Reference')
    move_type = fields.Selection([
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('internal', 'Internal Transfer'),
        ('manufacturing', 'Manufacturing'),
        ('adjustment', 'Adjustment'),
        ('landed_cost', 'Landed Cost'),
        ('other', 'Other'),
    ], string='Move Type')
    product_id = fields.Many2one('product.product', string='Product')
    product_code = fields.Char(string='Product Code')
    product_name = fields.Char(string='Product Name')
    location_id = fields.Many2one('stock.location', string='Location')
    location_name = fields.Char(string='Location')
    parent_location_id = fields.Many2one('stock.location', string='Parent Location')
    parent_location_name = fields.Char(string='Parent Location')
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure')
    uom_name = fields.Char(string='UoM')
    unit_cost = fields.Float(string='Unit Cost', digits='Product Price')
    value = fields.Float(string='Value', digits='Product Price')
    landed_cost_amount = fields.Float(string='Landed Cost', digits='Product Price')
    total_value = fields.Float(string='Total Value', digits='Product Price')
    balance_qty = fields.Float(string='Balance Qty', digits='Product Unit of Measure')
    balance_value = fields.Float(string='Balance Value', digits='Product Price')
    balance_total = fields.Float(string='Balance Total', digits='Product Price',
        help='Running balance of Value + Landed Cost. Only updates for rows with quantity movement.')
    origin = fields.Char(string='Source Document')
    partner_name = fields.Char(string='Partner')
