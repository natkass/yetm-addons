# add hs code tp purchase order line model
from odoo import fields, models, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    harmonized_code_id = fields.Many2one('import_fees.harmonized_code', store=True, readonly=True,
                                     help="Harmonized System Code, used to classify a product in import/export trade.", compute='_compute_harmonized_code_id')

    @api.depends('product_id')
    def _compute_harmonized_code_id(self):
        for record in self:
            record.harmonized_code_id = record.product_id.search_harmonized_code_id()
