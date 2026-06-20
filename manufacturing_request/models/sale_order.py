from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = "sale.order"

    manufacturing_request_count = fields.Integer(
        string="Manufacturing Requests",
        compute="_compute_manufacturing_request_count"
    )

    branch_id = fields.Many2one("res.branch", string="Branch", tracking=True)

    def _compute_manufacturing_request_count(self):
        for order in self:
            order.manufacturing_request_count = self.env["manufacturing.request"].search_count([
                ("sale_id", "=", order.id), ("state", "!=", "cancelled"),
            ])

    def action_open_manufacturing_request_wizard(self):
        self.ensure_one()
        return {
            "name": "Manufacturing Request",
            "type": "ir.actions.act_window",
            "res_model": "manufacturing.request.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_sale_id": self.id,
                "default_partner_id": self.partner_id.id,
                "default_customer_phone": self.partner_id.phone,
                "default_branch_id": self.branch_id.id,
            }
        }

    def action_view_manufacturing_requests(self):
        self.ensure_one()
        return {
            "name": "Manufacturing Requests",
            "type": "ir.actions.act_window",
            "res_model": "manufacturing.request",
            "view_mode": "tree,form",
            "domain": [("sale_id", "=", self.id)],
            "context": {"default_sale_id": self.id},
        }

class Branch(models.Model):
    _name = "res.branch"
    _description = "Branch"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date desc"

    name = fields.Char(string="Branch Name", tracking=True, required=True)