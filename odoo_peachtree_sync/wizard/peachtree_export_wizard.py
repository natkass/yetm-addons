import csv
import io
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PeachtreeExportWizard(models.TransientModel):
    _name = 'peachtree.export.wizard'
    _description = 'Export Sales to Peachtree CSV'

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    only_unexported = fields.Boolean(string='Only Unexported Invoices', default=True)
    mark_as_exported = fields.Boolean(string='Mark as Exported', default=True)
    include_credit_notes = fields.Boolean(string='Include Credit Notes', default=True)

    csv_file = fields.Binary(string='CSV File', readonly=True)
    csv_filename = fields.Char(string='Filename', readonly=True)
    export_count = fields.Integer(string='Invoices Exported', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft')

    def action_export(self):
        self.ensure_one()

        # Build domain for invoices
        domain = [
            ('move_type', 'in', self._get_move_types()),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
        ]

        if self.only_unexported:
            domain.append(('peachtree_exported', '=', False))

        invoices = self.env['account.move'].search(domain, order='invoice_date asc, name asc')

        if not invoices:
            raise UserError(_("No invoices found for the selected criteria."))

        # Generate CSV
        csv_data = self._generate_csv(invoices)

        # Mark as exported
        if self.mark_as_exported:
            invoices.write({'peachtree_exported': True})

        # Save file
        self.write({
            'csv_file': base64.b64encode(csv_data.encode('utf-8')),
            'csv_filename': 'SALES.CSV',
            'export_count': len(invoices),
            'state': 'done',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _get_move_types(self):
        types = ['out_invoice']
        if self.include_credit_notes:
            types.append('out_refund')
        return types

    def _generate_csv(self, invoices):
        output = io.StringIO()
        writer = csv.writer(output)

        # Peachtree 2010 Sales Journal CSV header (59 columns)
        header = [
            'Customer ID',                  # 1
            'Invoice/CM #',                 # 2
            'Apply to Invoice Number',      # 3
            'Credit Memo',                  # 4
            'Progress Billing Invoice',     # 5
            'Date',                         # 6
            'Ship By',                      # 7
            'Quote',                        # 8
            'Quote #',                      # 9
            'Quote Good Thru Date',         # 10
            'Drop Ship',                    # 11
            'Ship to Name',                 # 12
            'Ship to Address-Line One',     # 13
            'Ship to Address-Line Two',     # 14
            'Ship to City',                 # 15
            'Ship to State',                # 16
            'Ship to Zipcode',              # 17
            'Ship to Country',              # 18
            'Customer PO',                  # 19
            'Ship Via',                     # 20
            'Ship Date',                    # 21
            'Date Due',                     # 22
            'Discount Amount',              # 23
            'Discount Date',                # 24
            'Displayed Terms',              # 25
            'Sales Representative ID',      # 26
            'Accounts Receivable Account',  # 27
            'Sales Tax ID',                 # 28
            'Invoice Note',                 # 29
            'Note Prints After Line Items', # 30
            'Statement Note',               # 31
            'Stmt Note Prints Before Ref',  # 32
            'Internal Note',                # 33
            'Beginning Balance Transaction',# 34
            'Number of Distributions',      # 35
            'Invoice/CM Distribution',      # 36
            'Apply to Invoice Distribution',# 37
            'Apply To Sales Order',         # 38
            'Apply to Proposal',            # 39
            'Quantity',                     # 40
            'SO/Proposal Number',           # 41
            'Item ID',                      # 42
            'Serial Number',                # 43
            'SO/Proposal Distribution',     # 44
            'Description',                  # 45
            'G/L Account',                  # 46
            'Unit Price',                   # 47
            'Tax Type',                     # 48
            'UPC / SKU',                    # 49
            'Weight',                       # 50
            'Amount',                       # 51
            'Job ID',                       # 52
            'Sales Tax Agency ID',          # 53
            'Transaction Period',           # 54
            'Transaction Number',           # 55
            'Return Authorization',         # 56
            'Voided by Transaction',        # 57
            'Recur Number',                 # 58
            'Recur Frequency',              # 59
        ]
        writer.writerow(header)

        for invoice in invoices:
            customer_id = self._get_customer_id(invoice)
            invoice_number = invoice.name or ''
            invoice_date = '%d/%d/%s' % (invoice.invoice_date.month, invoice.invoice_date.day, invoice.invoice_date.strftime('%y')) if invoice.invoice_date else ''
            is_credit_note = invoice.move_type == 'out_refund'

            # Ship-to address
            ship_partner = invoice.partner_shipping_id or invoice.partner_id
            ship_name = (ship_partner.name or '')[:39]
            ship_addr1 = (ship_partner.street or '')[:30]
            ship_addr2 = (ship_partner.street2 or '')[:30]
            ship_city = (ship_partner.city or '')[:20]
            ship_state = (ship_partner.state_id.code or '')[:2]
            ship_zip = (ship_partner.zip or '')[:12]
            ship_country = (ship_partner.country_id.code or '')[:3]

            # Due date
            date_due = '%d/%d/%s' % (invoice.invoice_date_due.month, invoice.invoice_date_due.day, invoice.invoice_date_due.strftime('%y')) if invoice.invoice_date_due else ''

            # Payment terms
            payment_term = invoice.invoice_payment_term_id.name if invoice.invoice_payment_term_id else ''

            # AR Account
            ar_account = ''
            ar_line = invoice.line_ids.filtered(
                lambda l: l.account_id.account_type == 'asset_receivable'
            )[:1]
            if ar_line and ar_line.account_id:
                ar_account = ar_line.account_id.code or ''

            # Salesperson
            sales_rep = ''
            if invoice.invoice_user_id:
                sales_rep = (invoice.invoice_user_id.name or '')[:20]

            # Filter to product/service lines
            sale_lines = invoice.invoice_line_ids.filtered(
                lambda l: l.display_type == 'product'
            )

            num_distributions = len(sale_lines)
            if num_distributions == 0:
                continue

            for idx, line in enumerate(sale_lines):
                amount = -abs(line.price_subtotal)
                quantity = line.quantity
                unit_price = -abs(line.price_unit)

                # Credit notes: positive amounts (reversal)
                if is_credit_note:
                    amount = abs(line.price_subtotal)
                    unit_price = abs(line.price_unit)

                # GL Account
                gl_account = line.account_id.code or '' if line.account_id else ''

                # Item ID - uses Internal Reference only
                item_id = ''
                if line.product_id and line.product_id.default_code:
                    item_id = line.product_id.default_code[:20]

                # Tax type: 1=taxable, 2=non-taxable
                tax_type = 1 if line.tax_ids else 2

                # UPC / SKU
                barcode = (line.product_id.barcode or '') if line.product_id else ''

                # Weight
                weight = line.product_id.weight or 0.0 if line.product_id else 0.0

                # Description
                description = (line.name or line.product_id.name or '')[:160] if line.product_id else (line.name or '')[:160]

                # First line gets header-level data, subsequent lines are distribution-only
                is_first = idx == 0

                row = [
                    customer_id,                                        # 1  Customer ID
                    invoice_number,                                     # 2  Invoice/CM #
                    '',                                                 # 3  Apply to Invoice Number
                    'TRUE' if is_credit_note else 'FALSE',              # 4  Credit Memo
                    'FALSE',                                            # 5  Progress Billing Invoice
                    invoice_date if is_first else '',                   # 6  Date
                    '',                                                 # 7  Ship By
                    'FALSE',                                            # 8  Quote
                    '',                                                 # 9  Quote #
                    '',                                                 # 10 Quote Good Thru Date
                    'FALSE',                                            # 11 Drop Ship
                    ship_name if is_first else '',                      # 12 Ship to Name
                    ship_addr1 if is_first else '',                     # 13 Ship to Address-Line One
                    ship_addr2 if is_first else '',                     # 14 Ship to Address-Line Two
                    ship_city if is_first else '',                      # 15 Ship to City
                    ship_state if is_first else '',                     # 16 Ship to State
                    ship_zip if is_first else '',                       # 17 Ship to Zipcode
                    ship_country if is_first else '',                   # 18 Ship to Country
                    '',                                                 # 19 Customer PO
                    '',                                                 # 20 Ship Via
                    '',                                                 # 21 Ship Date
                    date_due if is_first else '',                       # 22 Date Due
                    '0.00',                                             # 23 Discount Amount
                    invoice_date if is_first else '',                   # 24 Discount Date
                    payment_term if is_first else '',                   # 25 Displayed Terms
                    sales_rep if is_first else '',                      # 26 Sales Representative ID
                    ar_account if is_first else '',                     # 27 Accounts Receivable Account
                    '',                                                 # 28 Sales Tax ID
                    '',                                                 # 29 Invoice Note
                    'FALSE',                                            # 30 Note Prints After Line Items
                    '',                                                 # 31 Statement Note
                    'FALSE',                                            # 32 Stmt Note Prints Before Ref
                    '',                                                 # 33 Internal Note
                    'FALSE',                                            # 34 Beginning Balance Transaction
                    str(num_distributions) if is_first else '',         # 35 Number of Distributions
                    idx + 1,                                            # 36 Invoice/CM Distribution
                    0,                                                  # 37 Apply to Invoice Distribution
                    'FALSE',                                            # 38 Apply To Sales Order
                    'FALSE',                                            # 39 Apply to Proposal
                    '{:.2f}'.format(quantity),                           # 40 Quantity
                    '',                                                 # 41 SO/Proposal Number
                    item_id,                                            # 42 Item ID
                    '',                                                 # 43 Serial Number
                    0,                                                  # 44 SO/Proposal Distribution
                    description,                                        # 45 Description
                    gl_account,                                         # 46 G/L Account
                    '{:.2f}'.format(unit_price),                         # 47 Unit Price
                    tax_type,                                           # 48 Tax Type
                    barcode,                                            # 49 UPC / SKU
                    '{:.2f}'.format(weight),                             # 50 Weight
                    '{:.2f}'.format(amount),                             # 51 Amount
                    '',                                                 # 52 Job ID
                    '',                                                 # 53 Sales Tax Agency ID
                    '',                                                 # 54 Transaction Period
                    '',                                                 # 55 Transaction Number
                    '',                                                 # 56 Return Authorization
                    '',                                                 # 57 Voided by Transaction
                    0,                                                  # 58 Recur Number
                    0,                                                  # 59 Recur Frequency
                ]
                writer.writerow(row)

        return output.getvalue()

    def _get_customer_id(self, invoice):
        partner = invoice.partner_id
        unique_ref = getattr(partner, 'x_studio_unique_reference', None)
        if unique_ref:
            return str(unique_ref)[:20]
        return (partner.name or 'UNKNOWN')[:20]

    def action_reset(self):
        """Reset to allow another export."""
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
        """Utility to reset the exported flag on invoices in the date range."""
        domain = [
            ('move_type', 'in', self._get_move_types()),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('peachtree_exported', '=', True),
        ]
        invoices = self.env['account.move'].search(domain)
        if not invoices:
            raise UserError(_("No exported invoices found in this date range."))
        invoices.write({'peachtree_exported': False})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reset Complete'),
                'message': _('%d invoices unmarked as exported.') % len(invoices),
                'type': 'success',
                'sticky': False,
            }
        }
