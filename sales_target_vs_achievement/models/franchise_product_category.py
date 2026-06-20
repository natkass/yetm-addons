from odoo import models, fields, api

class AccountManagerCustomer(models.Model):
    _name = "franchise.product.category"
    _description = "Franchise Product Category"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Reference', required=True,  default='New')
    

    product_tag_id = fields.Many2many(
        'product.tag',
        string="Product Tag",
        help="Select a product tag"
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

    # @api.model
    # def create(self, vals):
    #     if vals.get('name', 'New') == 'New':
    #         vals['name'] = self.env['ir.sequence'].next_by_code('franchise.product.category') or 'New'
            
    #     return super().create(vals)
