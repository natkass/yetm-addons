# delivery_print_limit/models/stock_picking.py
from odoo import models, fields, api, _

class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    allowed_delivery_prints = fields.Integer(
        string="Allowed delivery prints",
        default=1,
        help=(
            "Maximum number of times the Delivery Slip can be printed for pickings "
            "of this operation type. 0 means unlimited."
        ),
    )


class StockPicking(models.Model):
    _inherit = "stock.picking"

    delivery_print_count = fields.Integer(
        string="Delivery prints",
        default=0,
        readonly=True,
        copy=False,
    )
    delivery_last_print_user_id = fields.Many2one(
        "res.users",
        string="Last printed by",
        readonly=True,
        copy=False,
    )
    delivery_last_print_date = fields.Datetime(
        string="Last printed on",
        readonly=True,
        copy=False,
    )

    def action_reset_delivery_print_count(self):
        self.check_access_rights("write")
        self.check_access_rule("write")
        for picking in self:
            picking.write(
                {
                    "delivery_print_count": 0,
                    "delivery_last_print_user_id": False,
                    "delivery_last_print_date": False,
                }
            )
