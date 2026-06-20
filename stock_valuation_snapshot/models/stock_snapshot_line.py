# -*- coding: utf-8 -*-
from odoo import models, fields


class StockSnapshotLine(models.TransientModel):
    """Transient model to display stock snapshot valuation details."""
    _name = 'stock.snapshot.line'
    _description = 'Stock Snapshot Line'
    _order = 'product_code, location_name'

    wizard_id = fields.Many2one(
        'stock.snapshot.wizard',
        string='Wizard',
        ondelete='cascade'
    )
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
    amount = fields.Float(string='Amount', digits='Product Price')
    landed_cost = fields.Float(string='Landed Cost', digits='Product Price')
    total_amount = fields.Float(string='Total Amount', digits='Product Price')
