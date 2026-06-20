# models/sale_order.py
from odoo import models

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_open_non_standard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Configure Non-Standard Product",
            "res_model": "non.standard.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_order_id": self.id},
        }
