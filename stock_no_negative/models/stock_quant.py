from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools import config, float_compare

class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.constrains("product_id", "quantity")
    def check_negative_qty(self):
        # Skip the check if the context specifies so
        if self.env.context.get("skip_negative_qty_check"):
            return
        
        # Precision for quantity comparisons
        p = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        
        # Determine whether to check for negative quantities based on configuration
        check_negative_qty = (
            config.get("test_enable") and self.env.context.get("test_stock_no_negative")
        ) or not config.get("test_enable")
        if not check_negative_qty:
            return
        
        for quant in self:
            # Check whether negative stock is allowed for the product and location
            disallowed_by_product = (
                not quant.product_id.allow_negative_stock
                and not quant.product_id.categ_id.allow_negative_stock
            )
            
            # Fetch all locations in the hierarchy (including child locations)
            location_ids = self.env["stock.location"].search([("id", "child_of", quant.location_id.id)])
            disallowed_by_location = any(
                not location.allow_negative_stock for location in location_ids
            )
            
            # Raise a validation error if the quantity would result in negative stock
            if (
                float_compare(quant.quantity, 0, precision_digits=p) == -1
                and quant.product_id.type == "product"
                and disallowed_by_product
                and disallowed_by_location
            ):
                msg_add = ""
                if quant.lot_id:
                    msg_add = _(" lot {}").format(quant.lot_id.name_get()[0][1])
                raise ValidationError(
                    _(
                        "You cannot validate this stock operation because the "
                        "stock level of the product '{name}'{name_lot} would "
                        "become negative "
                        "({q_quantity}) on the stock location '{complete_name}' "
                        "and negative stock is "
                        "not allowed for this product and/or location."
                    ).format(
                        name=quant.product_id.display_name,
                        name_lot=msg_add,
                        q_quantity=quant.quantity,
                        complete_name=quant.location_id.complete_name,
                    )
                )
