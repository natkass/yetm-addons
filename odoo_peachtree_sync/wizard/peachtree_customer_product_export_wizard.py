import csv
import io
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PeachtreeCustomerProductExportWizard(models.TransientModel):
    _name = 'peachtree.customer.product.export.wizard'
    _description = 'Export Customers/Products to Peachtree CSV'

    export_type = fields.Selection([
        ('customer', 'Customers'),
        ('product', 'Products'),
    ], string='Export Type', required=True, default='customer')

    customer_filter = fields.Selection([
        ('all', 'All Customers'),
        ('has_invoice', 'Customers with Invoices'),
    ], string='Customer Filter', default='all')

    product_filter = fields.Selection([
        ('all', 'All Products'),
        ('sale_ok', 'Can be Sold'),
    ], string='Product Filter', default='sale_ok')

    only_unexported = fields.Boolean(string='Only Unexported', default=True)
    mark_as_exported = fields.Boolean(string='Mark as Exported', default=True)

    csv_file = fields.Binary(string='CSV File', readonly=True)
    csv_filename = fields.Char(string='Filename', readonly=True)
    export_count = fields.Integer(string='Records Exported', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft')

    def action_export(self):
        self.ensure_one()
        if self.export_type == 'customer':
            csv_data, records, filename = self._export_customers()
        else:
            csv_data, records, filename = self._export_products()

        if self.mark_as_exported:
            records.write({'peachtree_exported': True})

        self.write({
            'csv_file': base64.b64encode(csv_data.encode('utf-8')),
            'csv_filename': filename,
            'export_count': len(records),
            'state': 'done',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ── Customer Export ──────────────────────────────────────────────

    def _export_customers(self):
        if self.customer_filter == 'has_invoice':
            invoice_partners = self.env['account.move'].search([
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted'),
            ]).mapped('partner_id')
            partners = invoice_partners.sorted('name')
        else:
            partners = self.env['res.partner'].search([
                ('customer_rank', '>', 0),
            ], order='name asc')

        if self.only_unexported:
            partners = partners.filtered(lambda p: not p.peachtree_exported)

        if not partners:
            raise UserError(_("No customers found for the selected criteria."))

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        header = [
            'Customer ID',
            'Customer Name',
            'Contact',
            'Bill to Address-Line 1',
            'Bill to Address-Line 2',
            'Bill to City',
            'Bill to State',
            'Bill to Zip',
            'Bill to Country',
            'Ship to Name',
            'Ship to Address-Line 1',
            'Ship to Address-Line 2',
            'Ship to City',
            'Ship to State',
            'Ship to Zip',
            'Ship to Country',
            'Customer Type',
            'Telephone 1',
            'Telephone 2',
            'Fax Number',
            'E-mail',
            'GL Sales Account',
        ]
        writer.writerow(header)

        for partner in partners:
            customer_id = self._get_peachtree_customer_id(partner)

            # Try to find a shipping address (child of type 'delivery')
            ship_to = partner.child_ids.filtered(
                lambda c: c.type == 'delivery' and c.active
            )[:1] or partner

            # GL Sales Account: use default income account from partner's property
            gl_sales = ''
            if partner.property_account_receivable_id:
                gl_sales = partner.property_account_receivable_id.code or ''

            row = [
                customer_id,
                (partner.name or '')[:39],
                (partner.child_ids.filtered(lambda c: c.type == 'contact')[:1].name or '')[:19],
                (partner.street or '')[:30],
                (partner.street2 or '')[:30],
                (partner.city or '')[:20],
                (partner.state_id.code or '')[:2],
                (partner.zip or '')[:12],
                (partner.country_id.name or '')[:14],
                (ship_to.name or '')[:39],
                (ship_to.street or '')[:30],
                (ship_to.street2 or '')[:30],
                (ship_to.city or '')[:20],
                (ship_to.state_id.code or '')[:2],
                (ship_to.zip or '')[:12],
                (ship_to.country_id.name or '')[:14],
                '',  # Customer Type - left blank
                (partner.phone or '')[:20],
                (partner.mobile or '')[:20],
                '',  # Fax
                (partner.email or '')[:64],
                gl_sales,
            ]
            writer.writerow(row)

        return output.getvalue(), partners, 'CUSTOMERS.CSV'

    def _get_peachtree_customer_id(self, partner):
        unique_ref = getattr(partner, 'x_studio_unique_reference', None)
        if unique_ref:
            return str(unique_ref)[:20]
        return (partner.name or 'UNKNOWN')[:20]

    # ── Product Export ───────────────────────────────────────────────

    # Peachtree Item Class codes
    ITEM_CLASS_STOCK = 1
    ITEM_CLASS_NON_STOCK = 2
    ITEM_CLASS_SERVICE = 3
    ITEM_CLASS_LABOR = 4
    ITEM_CLASS_ASSEMBLY = 5

    # Peachtree Costing Method codes
    COST_FIFO = 1
    COST_LIFO = 2
    COST_AVERAGE = 0

    def _export_products(self):
        domain = [('type', 'in', ['consu', 'product', 'service'])]
        if self.product_filter == 'sale_ok':
            domain.append(('sale_ok', '=', True))
        if self.only_unexported:
            domain.append(('peachtree_exported', '=', False))

        products = self.env['product.product'].search(domain, order='default_code asc, name asc')

        if not products:
            raise UserError(_("No products found for the selected criteria."))

        output = io.StringIO()
        writer = csv.writer(output)

        header = self._get_item_csv_header()
        writer.writerow(header)

        for product in products:
            row = self._build_item_row(product)
            writer.writerow(row)

        return output.getvalue(), products, 'ITEMS.CSV'

    def _get_item_csv_header(self):
        header = [
            'Item ID', 'Item Description', 'Item Class', 'Inactive',
            'Subject to Commission', 'Description for Sales', 'Description for Purchases',
        ]
        # Sales Price 1-10, each with Calculation, Rounding, Rounding #
        for i in range(1, 11):
            header += [
                'Sales Price %d' % i,
                'Sales Price %d Calculation' % i,
                'Sales Price %d Rounding' % i,
                'Sales Price %d Rounding #' % i,
            ]
        header += [
            'Item Tax Type', 'Last Unit Cost', 'Costing Method',
            'G/L Sales Account', 'G/L Inventory Account', 'G/L COGS/Salary Acct',
            'UPC / SKU', 'Item Type', 'Location', 'Stocking U/M',
            'Weight', 'Minimum Stock', 'Reorder Quantity',
            'Vendor ID', 'Buyer ID', 'Alternate Vendor', 'Substitution',
            'Special Note', 'Master Stock Item ID',
        ]
        # Primary Attrib. ID/Desc 1-20
        for i in range(1, 21):
            header += ['Primary Attrib. ID %d' % i, 'Primary Attrib. Desc. %d' % i]
        # Secondary Attrib. ID/Desc 1-20
        for i in range(1, 21):
            header += ['Secondary Attrib. ID %d' % i, 'Secondary Attrib. Desc. %d' % i]
        header += [
            'Item Note', 'Print Components', 'Number of Components',
            'Primary Attrib. Name', 'Substock Primary Attrib. ID',
            'Substock Primary Attrib. Desc.', 'Secondary Attrib. Name',
            'Substock Second Attrib. ID', 'Substock Second Attrib. Desc.',
            'Warranty Period', 'Revision Number', 'Effective Date',
            'Component Number', 'Component ID', 'Quantity Needed', 'Part Number',
        ]
        return header

    def _build_item_row(self, product):
        item_id = self._get_peachtree_item_id(product)
        item_class = self._get_peachtree_item_class(product)

        # GL Accounts
        gl_sales = ''
        gl_inventory = ''
        gl_cogs = ''
        categ = product.categ_id
        if categ:
            income_acc = categ.property_account_income_categ_id
            if income_acc:
                gl_sales = income_acc.code or ''
            expense_acc = categ.property_account_expense_categ_id
            if expense_acc:
                gl_cogs = expense_acc.code or ''
            stock_acc = categ.property_stock_valuation_account_id
            if stock_acc:
                gl_inventory = stock_acc.code or ''

        # Costing method
        cost_method = self.COST_FIFO
        if categ and categ.property_cost_method == 'average':
            cost_method = self.COST_AVERAGE

        # Tax type: 0 = exempt, 1 = taxable
        tax_type = 1 if product.taxes_id else 0

        # UoM
        uom = product.uom_id.name if product.uom_id else ''

        row = [
            item_id,                                        # Item ID
            (product.name or '')[:160],                     # Item Description
            item_class,                                     # Item Class
            'TRUE' if not product.active else 'FALSE',      # Inactive
            'FALSE',                                        # Subject to Commission
            (product.description_sale or '')[:160],         # Description for Sales
            (product.description_purchase or '')[:160],     # Description for Purchases
        ]

        # Sales Price 1 = list_price, Sales Price 2-10 = 0
        for i in range(1, 11):
            price = product.list_price if i == 1 else 0
            row += [price, 'NC', 0, 0]

        row += [
            tax_type,                                       # Item Tax Type
            product.standard_price,                         # Last Unit Cost
            cost_method,                                    # Costing Method
            gl_sales,                                       # G/L Sales Account
            gl_inventory,                                   # G/L Inventory Account
            gl_cogs,                                        # G/L COGS/Salary Acct
            (product.barcode or ''),                        # UPC / SKU
            '',                                             # Item Type
            '',                                             # Location
            uom,                                            # Stocking U/M
            product.weight or 0,                            # Weight
            0,                                              # Minimum Stock
            0,                                              # Reorder Quantity
            '',                                             # Vendor ID
            '',                                             # Buyer ID
            '',                                             # Alternate Vendor
            '',                                             # Substitution
            '',                                             # Special Note
            '',                                             # Master Stock Item ID
        ]

        # Primary Attrib. ID/Desc 1-20 (empty)
        row += ['', ''] * 20
        # Secondary Attrib. ID/Desc 1-20 (empty)
        row += ['', ''] * 20

        row += [
            '',                                             # Item Note
            'FALSE',                                        # Print Components
            0,                                              # Number of Components
            '',                                             # Primary Attrib. Name
            '',                                             # Substock Primary Attrib. ID
            '',                                             # Substock Primary Attrib. Desc.
            '',                                             # Secondary Attrib. Name
            '',                                             # Substock Second Attrib. ID
            '',                                             # Substock Second Attrib. Desc.
            '',                                             # Warranty Period
            '',                                             # Revision Number
            '',                                             # Effective Date
            0,                                              # Component Number
            '',                                             # Component ID
            0,                                              # Quantity Needed
            '',                                             # Part Number
        ]

        return row

    def _get_peachtree_item_id(self, product):
        if product.default_code:
            return product.default_code[:20]
        return (product.name or 'ITEM')[:20]

    def _get_peachtree_item_class(self, product):
        if product.type == 'product':
            return self.ITEM_CLASS_STOCK
        elif product.type == 'consu':
            return self.ITEM_CLASS_NON_STOCK
        else:
            return self.ITEM_CLASS_SERVICE

    def action_reset(self):
        self.write({
            'state': 'draft',
            'csv_file': False,
            'csv_filename': False,
            'export_count': 0,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_reset_exported_flag(self):
        self.ensure_one()
        if self.export_type == 'customer':
            records = self.env['res.partner'].search([
                ('customer_rank', '>', 0),
                ('peachtree_exported', '=', True),
            ])
            label = _('customers')
        else:
            records = self.env['product.product'].search([
                ('peachtree_exported', '=', True),
            ])
            label = _('products')

        if not records:
            raise UserError(_("No exported %s found.") % label)

        records.write({'peachtree_exported': False})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reset Complete'),
                'message': _('%d %s unmarked as exported.') % (len(records), label),
                'type': 'success',
                'sticky': False,
            }
        }
