from odoo import models, fields, api

class AccountManagerCustomer(models.Model):
    _name = "account.manager.customer"
    _description = "Account Manager & Customers"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Reference', required=True, readonly=True, default='New')

    account_man_id = fields.Many2one(
        "hr.employee",
        string="Account Manager",
        required=True,
        tracking=True,
    )

    customer_ids = fields.Many2many(
        "res.partner",
        string="Assigned Customers",
        domain="[('category_id', 'ilike', 'Franchisee')]",
        tracking=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("locked", "Locked"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    

    def action_toggle_state(self):
        """Switch between Draft and Locked"""
        for rec in self:
            rec.state = "locked" if rec.state == "draft" else "draft"

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('account.manager') or 'New'
        return super().create(vals)
