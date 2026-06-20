from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    peachtree_exported = fields.Boolean(
        string='Exported to Peachtree',
        default=False,
        copy=False,
        readonly=True,
    )
