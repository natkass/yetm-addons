from odoo import models, fields, api
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    category_sequence=fields.Char(string="Generated Sequence", copy=False)

    @api.model
    def create(self, vals):
        if 'categ_id' in vals and not vals.get('default_code'):
            categ = self.env['product.category'].browse(vals['categ_id'])
            if not categ.sequence_prefix:
                raise UserError("Please define a Sequence Prefix on the product category before generating a sequence.")
            sequence_code = f'product.category.seq.{categ.id}'
            seq = self.env['ir.sequence'].search([('code', '=', sequence_code)], limit=1)
            if not seq:
                seq = self.env['ir.sequence'].create({
                    'name': f'{categ.name} Product Sequence',
                    'code': sequence_code,
                    'prefix': categ.sequence_prefix,
                    'padding': 4,
                    'implementation': 'standard',
                })
            vals['default_code'] = seq.next_by_code(sequence_code)
        return super(ProductTemplate, self).create(vals)

    def generate_category_sequence(self):
        for product in self:
            if product.categ_id:
                if not product.categ_id.sequence_prefix:
                    raise UserError("Please define a sequence prefix on the product category.")
                sequence_code = f'product.category.seq.{product.categ_id.id}'
                seq = self.env['ir.sequence'].search([('code', '=', sequence_code)], limit=1)
                if not seq:
                    seq = self.env['ir.sequence'].create({
                        'name': f'{product.categ_id.name} Product Sequence',
                        'code': sequence_code,
                        'prefix': product.categ_id.sequence_prefix,
                        'padding': 4,
                        'implementation': 'standard',
                    })
                product.sequence = seq.next_by_code(sequence_code)



class ProductCategory(models.Model):
    _inherit = 'product.category'

    sequence_prefix = fields.Char(string="Sequence Prefix")
