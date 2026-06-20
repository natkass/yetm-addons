from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    pos_order_id = fields.Many2one(
        'pos.order',
        string='POS Order',
        readonly=True
    )