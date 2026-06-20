from odoo import fields, models, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    is_landed_bill = fields.Boolean('Is Landed Costs Bill', default=False)



class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    harmonized_code_id = fields.Many2one('import_fees.harmonized_code', store=True, readonly=True,
                                     help="Harmonized System Code, used to classify a product in import/export trade.", compute='_compute_harmonized_code_id')

    @api.depends('product_id')
    def _compute_harmonized_code_id(self):
        for record in self:
            record.harmonized_code_id = record.product_id.search_harmonized_code_id()


