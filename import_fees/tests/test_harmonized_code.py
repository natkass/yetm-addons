# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError
from odoo.addons.import_fees.tests.test_landed_costs import ImportFeesTestLandedCosts  # Import the missing class

@tagged('post_install', '-at_install')
class TestHarmonizedCode(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.HarmonizedCode = cls.env['import_fees.harmonized_code']
        cls.ReceivedProductLine = cls.env['import_fees.received.product.line']
        cls.CustomsFees = cls.env['import_fees.customs_fees']
        cls.StockLandedCost = cls.env['stock.landed.cost']
        cls.company1 = cls.env['res.company'].create({'name': 'Test Company 1'})
        cls.company2 = cls.env['res.company'].create({'name': 'Test Company 2'})

    def test_create_harmonized_code(self):
        # Test creating a multi-company (no company) Harmonized System Code
        multi_company_code = self.HarmonizedCode.create({
            'name': '1234.56.78',
        })
        self.assertFalse(multi_company_code.company_ids, "Multi-company code should not have any companies")

        # Test creating a Harmonized System Code linked to specific companies
        specific_company_code = self.HarmonizedCode.create({
            'name': '9876.54.32',
            'company_ids': [(6, 0, [self.company1.id, self.company2.id])],
        })
        self.assertEqual(len(specific_company_code.company_ids), 2, "Specific company code should be linked to 2 companies")

    def test_uniqueness_constraint(self):
        # Create a multi-company code
        self.HarmonizedCode.create({
            'name': '1111.11.11',
        })

        # Try to create another multi-company code with the same name
        with self.assertRaises(ValidationError):
            self.HarmonizedCode.create({
                'name': '1111.11.11',
            })

        # Create a company-specific code
        self.HarmonizedCode.create({
            'name': '2222.22.22',
            'company_ids': [(6, 0, [self.company1.id])],
        })

        # Try to create another code with the same name for the same company
        with self.assertRaises(ValidationError):
            self.HarmonizedCode.create({
                'name': '2222.22.22',
                'company_ids': [(6, 0, [self.company1.id])],
            })

        # Create a code with the same name for a different company (should be allowed)
        company2_code = self.HarmonizedCode.create({
            'name': '2222.22.22',
            'company_ids': [(6, 0, [self.company2.id])],
        })
        self.assertTrue(company2_code, "Should be able to create a code with the same name for a different company")

    def test_received_product_line(self):
        # Create a Harmonized Code
        hs_code = self.HarmonizedCode.create({
            'name': '3333.33.33',
        })

        # Create a product
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
        })

        # Create a landed cost
        landed_cost = self.StockLandedCost.create({
            'name': 'Test Landed Cost',
        })

        # Create a received product line
        received_line = self.ReceivedProductLine.create({
            'landed_costs_id': landed_cost.id,
            'product_id': product.id,
            'quantity': 10,
            'price_unit': 100,
            'currency_id': self.env.ref('base.USD').id,
        })

        self.assertEqual(received_line.quantity, 10, "Quantity should be 10")
        self.assertEqual(received_line.price_unit, 100, "Price unit should be 100")

        # Test the compute method for hs_code_id
        product.write({'harmonized_code_id': hs_code.id})
        received_line._compute_hscode()
        self.assertEqual(received_line.hs_code_id, hs_code, "HS Code should be set correctly")

    def test_customs_fees(self):
        # Create a Harmonized Code
        hs_code = self.HarmonizedCode.create({
            'name': '4444.44.44',
        })

        # Create a landed cost
        landed_cost = self.StockLandedCost.create({
            'name': 'Test Landed Cost',
            
        })

        # Create customs fees
        customs_fees = self.CustomsFees.create({
            'landed_costs_id': landed_cost.id,
            'harmonized_code_id': hs_code.id,
            'rate': 0.1,
            'value': 1000,
            'amount': 100,
        })

        self.assertEqual(customs_fees.rate, 0.1, "Rate should be 0.1")
        self.assertEqual(customs_fees.value, 1000, "Declared value should be 1000")
        self.assertEqual(customs_fees.amount, 100, "Customs duties amount should be 100")
        
        
    def test_harmonized_code_company_context(self):
        hs_codes_from_demo_data = self.HarmonizedCode.search([]).ids

        hs_code_multi = self.HarmonizedCode.create({
            'name': '5555.55.55',
        })
        hs_code_company1 = self.HarmonizedCode.create({
            'name': '6666.66.66',
            'company_ids': [(6, 0, [self.company1.id])],
        })
        hs_code_company2 = self.HarmonizedCode.create({
            'name': '7777.77.77',
            'company_ids': [(6, 0, [self.company2.id])],
        })

        # Create a product template for company1
        product_tmpl = self.env['product.template'].with_company(self.company1).create({
            'name': 'Test Product Template',
            'company_id': self.company1.id,
        })

        # Test with company1 context
        product_tmpl.invalidate_model()
        expected_codes = set(hs_codes_from_demo_data + [hs_code_multi.id, hs_code_company1.id])
        found_codes = set(product_tmpl.allowed_harmonized_code_ids.ids)
        print(">>>>> found_codes", [it.name for it in self.env['import_fees.harmonized_code'].browse(found_codes)])
        print(">>>>> expected_codes", [it.name for it in self.env['import_fees.harmonized_code'].browse(expected_codes)])
        self.assertEqual(found_codes, expected_codes,
                        "Product template should only see multi-company and company1 harmonized codes")

        # Test setting harmonized code for company1
        product_tmpl.harmonized_code_id = hs_code_company1.id
        self.assertEqual(product_tmpl.harmonized_code_id, hs_code_company1,
                        "Should be able to set company1 harmonized code on product template")

