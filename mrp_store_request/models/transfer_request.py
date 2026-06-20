from odoo import fields, models


class TransferRequest(models.Model):
    _inherit = 'transfer.request'

    mrp_production_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order',
        readonly=True,
        ondelete='set null',
        index=True,
    )
