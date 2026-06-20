from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    peachtree_exported = fields.Boolean(
        string='Exported to Peachtree',
        default=False,
        copy=False,
        readonly=True,
    )
