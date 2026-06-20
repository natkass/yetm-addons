from odoo import models, fields

class ManufacturingRequestWizard(models.TransientModel):
    _name = "manufacturing.request.wizard"
    _description = "Manufacturing Request Wizard"

    responsible_id = fields.Many2one("res.users", string="Responsible", default=lambda self: self.env.user)
    partner_id = fields.Many2one("res.partner", string="Customer Name", required=True)
    customer_phone = fields.Char(related="partner_id.phone", readonly=True)
    branch_id = fields.Many2one("res.branch", string="Requesting Branch", required=True)
    promise_date = fields.Datetime(string="Promise Date", required=True)
    production_location_id = fields.Many2one(
        "stock.picking.type",
        string="Production Location",
        domain=[("code", "=", "mrp_operation")],  
        required=True
    )
    sale_id = fields.Many2one("sale.order", string="Sale Order")

    def action_submit(self):
        """Create Manufacturing Request from Sales Order + Wizard values"""
        self.ensure_one()
        sale = self.sale_id

        request = self.env["manufacturing.request"].create({
            "responsible_id": self.responsible_id.id,
            "partner_id": self.partner_id.id,
            "branch_id": self.branch_id.id,
            "promise_date": self.promise_date,
            "production_location_id": self.production_location_id.id,
            "sale_id": sale.id,
            "line_ids": [(0, 0, {
                "product_id": line.product_id.id,
                "product_uom_qty": line.product_uom_qty,
            }) for line in sale.order_line],
        })
        # Move to Submitted
        request.action_submit()

        # Post message in chatter
        sale.message_post(
            body=f"Manufacturing Request <b>{request.name}</b> has been created.",
            message_type="notification",
            subtype_xmlid="mail.mt_note",
        )

        return {"type": "ir.actions.act_window_close"}
