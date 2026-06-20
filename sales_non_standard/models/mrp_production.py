from odoo import models, fields, api

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    manufacturing_site = fields.Selection([
        ('dukem_foam', 'Dukem Foam'),
        ('dukem_bonded', 'Dukem Bonded'),
        ('hailegarment', 'Hailegarment Production'),
        ('kera_ifoam', 'Kera I Foam Production')
    ], string='Manufacturing Site', readonly=True, copy=False)
    
    @api.model
    def create(self, vals):
        res = super().create(vals)
        # If created from sale order, set manufacturing_site from sale order
        if 'origin' in vals and vals.get('origin'):
            sale_order = self.env['sale.order'].search([
                ('name', '=', vals['origin'])
            ], limit=1)
            if sale_order and sale_order.manufacturing_site:
                res.manufacturing_site = sale_order.manufacturing_site
        return res