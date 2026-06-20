from odoo import api, fields, models, _

import logging
logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)


class RepairOrder(models.Model):
    _name = 'repair.order'
    _description = 'Repair Order'

    name = fields.Char(string="Repair Name")
    # other fields...

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    expense_count = fields.Integer(string="Expense Count", default=0)
    repair_job_card_id = fields.Many2one('repair.order', string='Repair Job Card')
    pos_config_id = fields.Many2one(
        'pos.config',
        string='POS Config',
        required=False,
        help='Point of Sale Configuration related to this Sale Order'
    )
    
    # def _check_service_charge(self):
    #     if self.pos_config_id:
    #         if self.pos_config_id.pos_module_pos_service_charge:
    #             service_charge_tax_id = self.pos_config_id.global_service_charge.id
    #             for line in self.order_line:
    #                 product = line.product_id
    #                 line.tax_id = [(5, 0, 0)]
    #                 taxes = product.taxes_id
    #                 if taxes:
    #                     line.tax_id = [(6, 0, taxes.ids)]
                        
    #                 if service_charge_tax_id not in line.tax_id.ids:
    #                     line.tax_id = [(4, service_charge_tax_id)]
    #         else:
    #             for line in self.order_line:
    #                 product = line.product_id
    #                 line.tax_id = [(5, 0, 0)]
    #                 taxes = product.taxes_id
    #                 if taxes:
    #                     line.tax_id = [(6, 0, taxes.ids)]
    #                 if product:
    #                     if product.service_charge:
    #                         if product.service_charge.id not in line.tax_id.ids:
    #                             line.tax_id = [(4, product.service_charge.id)]        
                
    # @api.onchange('pos_config_id', 'order_line')
    # def _onchange_update_order_lines(self):
    #     self._check_service_charge()
        
    # def write(self, vals):
    #     res = super(SaleOrder, self).write(vals)
    #     self._check_service_charge()
    #     return res
