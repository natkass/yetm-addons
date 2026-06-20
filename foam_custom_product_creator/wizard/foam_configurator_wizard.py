from odoo import models, fields, api
from odoo.exceptions import UserError

class FoamConfiguratorWizard(models.TransientModel):
    _name = "foam.configurator.wizard"
    _description = "Foam Configurator Wizard"

    length = fields.Float("Length (cm)", required=True)
    width = fields.Float("Width (cm)", required=True)
    height = fields.Float("Height (cm)", required=True)
    quantity = fields.Integer("Quantity", default=1)
    foam_type = fields.Selection([('foam', 'Foam'), ('bonded', 'Bonded')], required=True)
    shape = fields.Char("Shape")
    fabric = fields.Boolean("Fabric")
    glue = fields.Boolean("Glue")
    seal = fields.Boolean("Seal")
    tape_edge = fields.Boolean("Tape Edge")
    packrise = fields.Boolean("Packrise")
    corner = fields.Boolean("Corner")

    def compute_and_add_product(self):
        # Volume calculation (m3)
        volume = (self.length / 100) * (self.width / 100) * (self.height / 100)
        if self.packrise:
            volume /= 2

        # Fake price for now (e.g. 1000 ETB per m3)
        price_per_m3 = 1000
        price = volume * price_per_m3

        product = self.env['product.product'].create({
            'name': f"{self.height} {self.length} {self.width} {self.shape or ''} {self.foam_type}",
            'type': 'product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'uom_po_id': self.env.ref('uom.product_uom_unit').id,
            'list_price': price,
        })

        sale_order_id = self.env.context.get('active_id')
        sale_order = self.env['sale.order'].browse(sale_order_id)
        if not sale_order:
            raise UserError("No active sale order found.")

        sale_order.order_line.create({
            'order_id': sale_order.id,
            'product_id': product.id,
            'product_uom_qty': self.quantity,
            'price_unit': product.list_price,
            'name': product.name,
            'product_uom': product.uom_id.id,
        })
