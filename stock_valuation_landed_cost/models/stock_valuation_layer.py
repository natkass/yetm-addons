# -*- coding: utf-8 -*-
from odoo import fields, models


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    landed_cost_amount = fields.Monetary(
        string='Landed Cost',
        currency_field='currency_id',
        default=0.0,
        readonly=True,
        help='Total landed cost amount distributed to this valuation layer'
    )
