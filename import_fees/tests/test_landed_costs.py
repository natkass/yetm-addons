# -*- coding: utf-8 -*-

from odoo.addons.stock_landed_costs.tests.common import TestStockLandedCostsCommon
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare
from odoo import fields
from datetime import datetime, timedelta
import time


@tagged('post_install', '-at_install')
class ImportFeesTestLandedCosts(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        #enable EUR currency
        cls.env.ref('base.EUR').active = True

        cls.product_data = [
            ('5320-24T-8XE', 4, 1163.82, '8517.62.90'),
            ('5320-24P-8XE', 4, 1565.09, '8517.62.90'),
            ('5320-48T-8XE', 4, 1484.12, '8517.62.90'),
            ('5320-24T-8XE', 3, 1141.00, '8517.62.90'),
            ('5420F-16MW-32P-4XE', 2, 4126.98, '8517.62.90'),
            ('AP510C-WR', 20, 455.50, '8517.62.10'),
            ('XN-ACPWR', 1, 645.40, '8504.40.90'),
            ('<UNKNOWN>', 2, 53.10, '8504.40.90'),
        ]
        cls.categ = cls.env['product.category'].create({
            'name': 'Test Category',
            'property_cost_method': 'average',
            'property_valuation': 'real_time',
        })

        cls.products = {}
        for name, qty, price, hs_code in cls.product_data:
            product = cls.env['product.product'].create({
                'name': name,
                'type': 'product',
                'categ_id': cls.categ.id,
                'standard_price': price,
                'cost_method': 'average',
            })
            harmonized_code = cls.env['import_fees.harmonized_code'].find_or_create(hs_code)
            product.write({'harmonized_code_id': harmonized_code.id})
            cls.products[name] = {'product': product, 'qty': qty, 'price': price}

        cls.vendor = cls.env['res.partner'].create({
            'name': 'EXTREME',
            'supplier_rank': 1,
        })

        cls.po = cls.env['purchase.order'].create({
            'partner_id': cls.vendor.id,
            'order_line': [
                (0, 0, {
                    'product_id': cls.products[name]['product'].id,
                    'product_qty': cls.products[name]['qty'],
                    'price_unit': cls.products[name]['price'],
                }) for name in cls.products
            ],
            'currency_id': cls.env.ref('base.EUR').id,
        })
        cls.po.button_confirm()

        # Receive the products
        picking = cls.po.picking_ids[0]
        picking.action_confirm()
        picking.action_assign()
        for move_line in picking.move_line_ids:
            move_line.quantity = move_line.quantity_product_uom
        picking.button_validate()

        # Create vendor bill
        action = cls.po.action_create_invoice()
        cls.invoice = cls.env['account.move'].browse(action['res_id'])
        cls.invoice.invoice_date = fields.Date.today()
        cls.invoice.action_post()

        # Set currency rates
        cls.env['res.currency.rate'].create({
            'name': fields.Date.today(),
            'rate': 1.0 / 1.1,
            'currency_id': cls.env.ref('base.EUR').id,
            'company_id': cls.env.company.id,
        })


    def test_hs_code_application(self):
        for product_data in self.product_data:
            product_name, _, _, expected_hs_code = product_data
            product = self.products[product_name]['product']
            self.assertEqual(product.harmonized_code_id.name, expected_hs_code,
                             f"Incorrect HS Code for product {product_name}")

    def test_custom_split_method(self):
        landed_cost = self.env['stock.landed.cost'].create({
            'picking_ids': [(4, self.po.picking_ids[0].id)],
            'account_journal_id': self.env['account.journal'].search([('type', '=', 'general')], limit=1).id,
            'vendor_bill_ids': [(4, self.invoice.id)],
            'bank': 126153.86,
            'clearance': 27553.50,
            'freight': 190260.58,
        })

        landed_cost.calc_customs_fees_and_open()
        
        # Set split method to 'by_hscode' for customs duties
        customs_cost_line = landed_cost.cost_lines.filtered(lambda l: l.product_id == self.env.ref('import_fees.customs'))
        customs_cost_line.write({'split_method': 'by_hscode'})

        landed_cost.compute_landed_cost()

        # Check if costs are distributed correctly based on HS codes
        hs_code_costs = {}
        for valuation in landed_cost.valuation_adjustment_lines:
            if valuation.cost_line_id == customs_cost_line:
                hs_code = valuation.product_id.harmonized_code_id.name
                hs_code_costs[hs_code] = hs_code_costs.get(hs_code, 0) + valuation.additional_landed_cost


    def test_create_landed_bill(self):
        landed_cost = self.env['stock.landed.cost'].create({
            'picking_ids': [(4, self.po.picking_ids[0].id)],
            'account_journal_id': self.env['account.journal'].search([('type', '=', 'general')], limit=1).id,
            'vendor_bill_ids': [(4, self.invoice.id)],
            'bank': 126153.86,
            'clearance': 27553.50,
            'freight': 190260.58,
        })

        landed_cost.calc_customs_fees_and_open()
        landed_cost.compute_landed_cost()
        landed_cost.button_validate()

        # Create landed cost bill
        result = landed_cost.button_create_landed_bill()
        
        self.assertEqual(result['type'], 'ir.actions.act_window', "Should return an action to open the created bill")
        self.assertEqual(result['res_model'], 'account.move', "Should create an account move")
        
        bill = self.env['account.move'].browse(result['res_id'])
        self.assertTrue(bill, "Landed cost bill should be created")
        self.assertEqual(bill.move_type, 'in_invoice', "Created bill should be a vendor bill")
        self.assertEqual(bill.invoice_origin, landed_cost.name, "Bill should reference the landed cost")

    def test_error_handling(self):
        # Test creating landed cost without picking
        with self.assertRaises(UserError):
            self.env['stock.landed.cost'].create({
                'account_journal_id': self.env['account.journal'].search([('type', '=', 'general')], limit=1).id,
                'bank': 126153.86,
                'clearance': 27553.50,
                'freight': 190260.58,
            }).calc_customs_fees_and_open()

    def test_currency_conversion(self):
        landed_cost = self.env['stock.landed.cost'].create({
            'picking_ids': [(4, self.po.picking_ids[0].id)],
            'vendor_bill_ids': [(4, self.invoice.id)],
            'account_journal_id': self.env['account.journal'].search([('type', '=', 'general')], limit=1).id,
            'bank': 126153.86,
            'clearance': 27553.50,
            'freight': 190260.58,
        })

        landed_cost.calc_customs_fees_and_open()

        # Check if the currency conversion is correct
        total_eur = sum(line.price_unit * line.product_qty for line in self.po.order_line)
        expected_usd = total_eur * 1.1  # Using the exchange rate we set up

        self.assertAlmostEqual(landed_cost.amount_local_currency, expected_usd, 1,
                               "Incorrect currency conversion from EUR to USD")

if __name__ == '__main__':
    from odoo.tests.common import tagged
    from odoo.tests import runner
    runner.run_tests(['test_landed_costs'])
