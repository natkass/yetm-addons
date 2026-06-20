from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    peachtree_exported = fields.Boolean(
        string='Exported to Peachtree',
        default=False,
        copy=False,
        readonly=True,
    )
