# -*- coding: utf-8 -*-
from odoo import models


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def button_validate(self):
        res = super().button_validate()

        SVL = self.env['stock.valuation.layer']

        for cost in self:
            for line in cost.valuation_adjustment_lines:
                if line.move_id and line.additional_landed_cost:
                    # Find original valuation layers for this move (incoming, quantity > 0)
                    original_layers = line.move_id.stock_valuation_layer_ids.filtered(
                        lambda l: not l.stock_landed_cost_id and l.quantity > 0
                    )

                    if not original_layers:
                        continue

                    # Calculate total original quantity across all incoming layers for this move
                    total_original_qty = sum(original_layers.mapped('quantity'))
                    if not total_original_qty:
                        continue

                    for orig_layer in original_layers:
                        # Proportion of landed cost for this specific layer
                        layer_proportion = orig_layer.quantity / total_original_qty
                        layer_landed_cost = line.additional_landed_cost * layer_proportion

                        # Original layer gets the FULL landed cost (positive)
                        orig_layer.landed_cost_amount += layer_landed_cost

                        # Get the original incoming quantity
                        original_qty = orig_layer.quantity
                        # Calculate per-unit landed cost
                        per_unit_landed_cost = layer_landed_cost / original_qty if original_qty else 0

                        # Find outgoing (sold) layers for the same product
                        # that were created after the original layer
                        sold_layers = SVL.search([
                            ('product_id', '=', orig_layer.product_id.id),
                            ('company_id', '=', orig_layer.company_id.id),
                            ('quantity', '<', 0),
                            ('stock_landed_cost_id', '=', False),
                            ('create_date', '>=', orig_layer.create_date),
                        ])

                        # Distribute to sold layers (negative amount)
                        # Each sold layer gets: per_unit_landed_cost * sold_quantity (as negative)
                        for sold_layer in sold_layers:
                            # sold_layer.quantity is negative, so this will be negative
                            sold_layer.landed_cost_amount += per_unit_landed_cost * sold_layer.quantity

        return res
