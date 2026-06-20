from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from odoo.tools import float_compare, date_utils, email_split, email_re, html_escape, is_html_empty
from odoo.tools.misc import formatLang, format_date, get_lang
import logging
from datetime import date, timedelta
from collections import defaultdict
from contextlib import contextmanager
from itertools import zip_longest
from hashlib import sha256
from json import dumps
import ast
import json
import re
import warnings

_logger = logging.getLogger(__name__)

# class CustomMrpProduction(models.Model):
#     _inherit = 'mrp.production'  

#     @api.ondelete(at_uninstall=False)
#     def _unlink_except_done(self):
#         return super()._unlink_except_done()


@api.ondelete(at_uninstall=False)
def _unlink_except_done(self):
    if any(production.state == 'done' for production in self):
        raise UserError(_('Cannot delete a manufacturing order in the "done" state.'))

def unlink(self):
    # self.action_cancel()
    return super(CustomMrpProduction, self).unlink()







################### Back Date Block for inventory, invoices and mrp based on sale order date ######################
# class StockDate(models.Model):
#     _inherit = "stock.picking"

#     def _set_scheduled_date(self):
#         for picking in self:
#             picking.move_ids.write({'date': picking.scheduled_date})

#     def _action_done(self):
#         super(StockDate, self)._action_done()
#         if self.picking_type_code == 'outgoing' and 'Return' not in self.origin:
#             sale_date = self.sale_id.date_order
#             if isinstance(sale_date, bool):  # Ensure sale_date is not a boolean
#                 sale_date = fields.Datetime.now()  # Or set to a default datetime
#             self.write({"date": sale_date, "date_done": sale_date, "scheduled_date": sale_date})

#             if self.move_ids:
#                 self.move_ids.write({"date": sale_date})
#             if self.move_line_ids:
#                 self.move_line_ids.write({"date": sale_date})

#         if self.picking_type_code == 'mrp_operation' and 'Return' not in self.origin:
#             scheduled_date = self.scheduled_date
#             if isinstance(scheduled_date, bool):  # Ensure scheduled_date is not a boolean
#                 scheduled_date = fields.Datetime.now()  # Or set to a default datetime
#             self.write({"date": scheduled_date, "date_done": scheduled_date})

#             if self.move_ids:
#                 self.move_ids.write({"date": scheduled_date})
#             if self.move_line_ids:
#                 self.move_line_ids.write({"date": scheduled_date})


#     def button_validate(self):
#         try:
#             _logger.info("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<THis is doing something")
#             if (self.scheduled_date and self.picking_type_code == 'outgoing') or (self.scheduled_date and self.picking_type_code == 'incoming') or  (self.scheduled_date and self.picking_type_code == 'mrp_operation'):
#                 _logger.error("An error occurred in button_validate before catch: %s", self.scheduled_date)
#                 return super(
#                     StockDate, self.with_context(force_period_date=self.scheduled_date)
#                 ).button_validate()           
#             else:
#                 return super(StockDate, self).button_validate()
#         except Exception as e:
#             _logger.error("An error occurred in button_validate: %s", str(e))

# class StockValuationLayer(models.Model):
#     _inherit = "stock.valuation.layer"
#     _order = "id"
#     create_date = fields.Datetime(related="stock_move_id.date",store=True, readonly=False)



# # Start Mrp Backdate Block
# class MrpOrd(models.Model):
#     _inherit = 'mrp.production'

#     def action_confirm(self):
#         _logger.info("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<THis is doing something")
#         _logger.info("\n=== [MO CONFIRM] Starting confirmation for %d MO(s) ===", len(self))

#         sale_order = self.env['sale.order']
#         _logger.info("\n=== [MO CONFIRM] Sale Order Model: %s", sale_order)
        
#         for production in self:
#             _logger.info("\n[MO CONFIRM] Processing MO ID: %s, Name: %s, State: %s", production.id, production.name, production.state)
#             _logger.info(production.origin)

#             sale_order_rec = sale_order.search([('name', '=', production.origin)], limit=1)
#             _logger.info("\n=== [MO CONFIRM] Sale Order Record: %s", sale_order_rec)
#             if sale_order_rec:
#                 _logger.info("\n=== [MO CONFIRM] Sale Order Record: %s", sale_order_rec)
#                 planned_start_date = sale_order_rec.date_order
#                 _logger.info("\n=== [MO CONFIRM] Planned Start Date: %s", planned_start_date)
#                 if isinstance(planned_start_date, bool):  # Ensure planned_start_date is not a boolean
#                     planned_start_date = fields.Datetime.now()  # Or set to a default datetime
#                 production.write({'date_start': planned_start_date})
#                 _logger.info("\n=== [MO CONFIRM] Planned Start Date: %s", planned_start_date)
#                 super(MrpOrd, production).action_confirm()
#                 if sale_order_rec.picking_ids:
#                     all_done = True
#                     mrp_orders = self.env['mrp.production'].search([('origin', '=', production.origin), ('id', '!=', production.id)])
#                     for mo in mrp_orders:
#                         _logger.info("\n=== [MO CONFIRM] MRPOrder Record: %s", mo)              
#                         if mo.state != 'done':
#                             all_done = False
#                             break
#                     if all_done:
#                         _logger.info("\n=== [MO CONFIRM] All MRPOrder Records are done")
#                         for picking in sale_order_rec.picking_ids:
#                             _logger.info("\n=== [MO CONFIRM] Picking Record: %s", picking)
#                             picking.action_assign()
#                             _logger.info("\n=== [MO CONFIRM] Picking Record: %s", picking)
#                             picking.action_confirm()
#                             _logger.info("\n=== [MO CONFIRM] Picking Record: %s", picking)
#                             for mv in picking.move_ids_without_package: 
#                                 _logger.info("\n=== [MO CONFIRM] Move Record: %s", mv)
#                                 mv.quantity_done = mv.product_uom_qty
#                             _logger.info("\n=== [MO CONFIRM] Picking Record: %s", picking)
#                             picking.button_validate()
#                             _logger.info("\n=== [MO CONFIRM] Picking Record: %s", picking)
#             else:
#                 super(MrpOrd, production).action_confirm()
#         return True         


#     def button_mark_done(self):
#         _logger.info("\n=== [MO CONFIRM] Button Mark Done")
#         records = self.env['stock.valuation.layer'].search([])
#         _logger.info("\n=== [MO CONFIRM] Records: %s", records)
#         # _logger.info(f"{records.read()}")
#         for x in records:
#             _logger.info("\n=== [MO CONFIRM] Record: %s", x)
#             if(not x.create_date):
#                 _logger.info("\n=== [MO CONFIRM] Record: %s", x)
#                 _logger.info(f"MoveDate{x.stock_move_id.date}")
#                 x.create_date = x.stock_move_id.date
#                 _logger.info("Making corrections to the broken fields")
#         res = super(MrpOrd, self).button_mark_done()
#         _logger.info("\n=== [MO CONFIRM] Button Mark Done")
#         if res:
#             stock_moves = self.env['stock.move'].search([('reference', '=', self.name)])
#             product_moves = self.env['stock.move.line'].search([('reference', '=', self.name)])
#             # account_moves = self.env['account.move'].search([('ref', '=', self.name)])
#             account_moves = self.env['account.move'].search([('ref', 'ilike', '%' + self.name + '%')])
            
#             _logger.info("\n=== [MO CONFIRM] Stock Moves: %s", stock_moves)
#             _logger.info("\n=== [MO CONFIRM] Product Moves: %s", product_moves)
#             _logger.info("\n=== [MO CONFIRM] Account Moves: %s", account_moves)
            
#             for move in stock_moves:
#                 _logger.info("\n=== [MO CONFIRM] Move: %s", move)
#                 move.date = self.date_planned_start
#             for move_line in product_moves:
#                 _logger.info("\n=== [MO CONFIRM] Move Line: %s", move_line)
#                 move_line.date = self.date_planned_start
#             for acc in account_moves:
#                 _logger.info("\n=== [MO CONFIRM] Account Move: %s", acc)
#                 acc.date=self.date_planned_start
#         return res

#     # End MRP BackDate Block



# class SaleO(models.Model):
#     _inherit="sale.order"

#     def _prepare_confirmation_values(self):
#         return {
#             'state': 'sale',
#             'date_order': self.date_order
#         }
#     def _prepare_invoice(self):
#         self.ensure_one()
#         journal = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
#         if not journal:
#             raise UserError(_('Please define an accounting sales journal for the company %s (%s).', self.company_id.name, self.company_id.id))

#         invoice_vals = {
#             'ref': self.client_order_ref or '',
#             'move_type': 'out_invoice',
#             'narration': self.note,
#             'currency_id': self.pricelist_id.currency_id.id,
#             'campaign_id': self.campaign_id.id,
#             'medium_id': self.medium_id.id,
#             'source_id': self.source_id.id,
#             'user_id': self.user_id.id,
#             'invoice_user_id': self.user_id.id,
#             'team_id': self.team_id.id,
#             'partner_id': self.partner_invoice_id.id,
#             'partner_shipping_id': self.partner_shipping_id.id,
#             'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(self.partner_invoice_id.id)).id,
#             'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
#             'journal_id': journal.id,  # company comes from the journal
#             'invoice_origin': self.name,
#             'invoice_payment_term_id': self.payment_term_id.id,
#             'payment_reference': self.reference,
#             'transaction_ids': [(6, 0, self.transaction_ids.ids)],
#             'invoice_line_ids': [],
#             'company_id': self.company_id.id,
#             'invoice_date': self.date_order,
#             'invoice_date_due': self.date_order

#         }
#         return invoice_vals

# class CustomAccountMove(models.Model):
#     _inherit = "account.move"
     
#     def _post(self, soft=True):
#         if soft:
#             future_moves = self.filtered(lambda move: move.date > fields.Date.context_today(self))
#             future_moves.auto_post = True
#             for move in future_moves:
#                 # msg = _('This move will be posted at the accounting date: %(date)s', date=format_date(self.env, move.date))
#                 msg="Hello"
#                 move.message_post(body=msg)
#             to_post = self - future_moves
#         else:
#             to_post = self

#         # `user_has_group` won't be bypassed by `sudo()` since it doesn't change the user anymore.
#         if not self.env.su and not self.env.user.has_group('account.group_account_invoice'):
#             raise AccessError(_("You don't have the access rights to post an invoice."))
#         for move in to_post:
#             if move.partner_bank_id and not move.partner_bank_id.active:
#                 raise UserError(_("The recipient bank account link to this invoice is archived.\nSo you cannot confirm the invoice."))
#             if not move.line_ids.filtered(lambda line: not line.display_type):
#                 raise UserError(_('You need to add a line before posting.'))
#             if move.auto_post and move.date > fields.Date.context_today(self):
#                 date_msg = move.date.strftime(get_lang(self.env).date_format)
#                 raise UserError(_("This move is configured to be auto-posted on %s", date_msg))
#             if not move.journal_id.active:
#                 raise UserError(_(
#                     "You cannot post an entry in an archived journal (%(journal)s)",
#                     journal=move.journal_id.display_name,
#                 ))

#             if not move.partner_id:
#                 if move.is_sale_document():
#                     raise UserError(_("The field 'Customer' is required, please complete it to validate the Customer Invoice."))
#                 elif move.is_purchase_document():
#                     raise UserError(_("The field 'Vendor' is required, please complete it to validate the Vendor Bill."))

#             if move.is_invoice(include_receipts=True) and float_compare(move.amount_total, 0.0, precision_rounding=move.currency_id.rounding) < 0:
#                 raise UserError(_("You cannot validate an invoice with a negative total amount. You should create a credit note instead. Use the action menu to transform it into a credit note or refund."))

#             if move.display_inactive_currency_warning:
#                 raise UserError(_("You cannot validate an invoice with an inactive currency: %s",
#                                   move.currency_id.name))
#             if not move.invoice_date:
#                 if move.is_sale_document(include_receipts=True):
#                     move.invoice_date = fields.Date.context_today(self)
#                     move.with_context(check_move_validity=False)._onchange_invoice_date()
#                 elif move.is_purchase_document(include_receipts=True):
#                     raise UserError(_("The Bill/Refund date is required to validate this document."))

#             affects_tax_report = move._affect_tax_report()
#             lock_dates = move._get_violated_lock_dates(move.date, affects_tax_report)
#             if lock_dates:
#                 move.date = move._get_accounting_date(move.invoice_date or move.date, affects_tax_report)
#                 move.with_context(check_move_validity=False)._onchange_currency()

#         # Create the analytic lines in batch is faster as it leads to less cache invalidation.
#         to_post.mapped('line_ids').create_analytic_lines()

#         for move in to_post:
#             wrong_lines = move.is_invoice() and move.line_ids.filtered(lambda aml: aml.partner_id != move.commercial_partner_id and not aml.display_type)
#             if wrong_lines:
#                 wrong_lines.write({'partner_id': move.commercial_partner_id.id})

#         to_post.write({
#             'state': 'posted',
#             'posted_before': True,
#         })

#         for move in to_post:
#             move.message_subscribe([p.id for p in [move.partner_id] if p not in move.sudo().message_partner_ids])

#             # Compute 'ref' for 'out_invoice'.
#             if move._auto_compute_invoice_reference():
#                 to_write = {
#                     'payment_reference': move._get_invoice_computed_reference(),
#                     'line_ids': []
#                 }
#                 for line in move.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable')):
#                     to_write['line_ids'].append((1, line.id, {'name': to_write['payment_reference']}))
#                 move.write(to_write)

#         for move in to_post:
#             if move.is_sale_document() \
#                     and move.journal_id.sale_activity_type_id \
#                     and (move.journal_id.sale_activity_user_id or move.invoice_user_id).id not in (self.env.ref('base.user_root').id, False):
#                 move.activity_schedule(
#                     date_deadline=min((date for date in move.line_ids.mapped('date_maturity') if date), default=move.date),
#                     activity_type_id=move.journal_id.sale_activity_type_id.id,
#                     summary=move.journal_id.sale_activity_note,
#                     user_id=move.journal_id.sale_activity_user_id.id or move.invoice_user_id.id,
#                 )

#         customer_count, supplier_count = defaultdict(int), defaultdict(int)
#         for move in to_post:
#             if move.is_sale_document():
#                 customer_count[move.partner_id] += 1
#             elif move.is_purchase_document():
#                 supplier_count[move.partner_id] += 1
#         for partner, count in customer_count.items():
#             (partner | partner.commercial_partner_id)._increase_rank('customer_rank', count)
#         for partner, count in supplier_count.items():
#             (partner | partner.commercial_partner_id)._increase_rank('supplier_rank', count)

#         # Trigger action for paid invoices in amount is zero
#         to_post.filtered(
#             lambda m: m.is_invoice(include_receipts=True) and m.currency_id.is_zero(m.amount_total)
#         ).action_invoice_paid()

#         to_post._check_balanced()
#         return to_post


################################################################################################































# class Expense_tax(models.Model):
#     _inherit="hr.expense"
#     tax_ids = fields.Many2many('account.tax', 'expense_tax', 'expense_id', 'tax_id',
#         compute='_compute_from_product_id_company_id', store=True, readonly=False,
#         domain="[('company_id', '=', company_id)]", string='Taxes',
#         help="The taxes should be \"Included In Price\"")

class NonStandardValue(models.Model):
    _name = "non_standard.value"
    _description = "Is a value to be set"

    name = fields.Char(string='Name')

    unit_price = fields.Integer(string="Price", default=1, required=True)
    description = fields.Char(string="Description")
    product = fields.Many2one("product.product", string="Product")

    @api.onchange('product')
    def _onchange_value(self):
        print(self.product.list_price)
        self.unit_price = self.product.list_price
        self.name = self.product.display_name

class FashaVariance(models.Model):
    _name = "non_standard.fasha.variance"
    _description = "This is Fasha variance"

    size = fields.Selection([
        ('6', '6'),
        ('12', '12'),
        ('16', '16'),
        ('20', '20'),
        ('24', '24'),
        ('28','28')
    ], default='6', string='Size')
    price = fields.Float('Price')
    fasha_id = fields.Many2one('non_standard.fasha')


class NonStandardFasha(models.Model):
    _name = "non_standard.fasha"
    _description = "This is Fasha"

    name = fields.Char('Name')
    size = fields.Selection([
        ('6', '6'),
        ('12', '12'),
        ('16', '16'),
        ('20', '20'),
        ('24', '24')
    ], default='6', string='Size')

    unit_price = fields.Float(string="Price", default=1, required=True)
    description = fields.Char(string="Description")
    product = fields.Many2one("product.product", string="Product")
    variant = fields.One2many( "non_standard.fasha.variance",'fasha_id',string="Size Variant")

    @api.onchange('product')
    def _onchange_value(self):
        print(self.product.list_price)
        self.unit_price = self.product.list_price
        self.name = self.product.display_name


class NonStandardSeal(models.Model):
    _name = "non_standard.seal"
    _description = "This is seal"

    name = fields.Char(string='Name', default = "Name")
    unit_price = fields.Float(string="Unit Price")
    product = fields.Many2one("product.product", string="Product")




class NonStandardValue(models.Model):
    _name = "non_standard.fabric"
    _description = "This is fabric"

    size = fields.Float(string="Size", default=1, required=True)
    description = fields.Char(string="Description")
    name = fields.Char(string='Name', default = "Name")
    unit_price = fields.Float(string="Unit Price")
    product = fields.Many2one("product.product", string="Product")

    @api.onchange('product')
    def _onchange_value(self):
        print(self.product.list_price)
        self.unit_price = self.product.list_price
        self.name = self.product.display_name


class ExtendSale(models.Model):
    _inherit = 'sale.order'
    
    # Simplified expense_count field without the problematic relationship
    # expense_count = fields.Integer(string="Expense Count", default=0)
    final_total_all = fields.Float(string="Final Total", default=0)
    

    @api.onchange('volume_price','seal_total','glu_total','tape_edge_total','fabric_total_1','fabric_total_2')
    def _onchange_final_total_all(self):
        self.final_total_all = self.volume_price + self.seal_total + self.glu_total + self.tape_edge_total + self.fabric_total_1 + self.fabric_total_2   

    



    non_standard = fields.Boolean(string='Non Standard', default=False)
    value = fields.Many2one("product.template", string="Value", domain="['|',('products', '=', 'Foam'),('products', '=', 'Bonded')]")
    
    # Manufacturing site field
    manufacturing_site = fields.Selection([
        ('dukem_foam', 'Dukem Foam'),
        ('dukem_bonded', 'Dukem Bonded'),
        ('hailegarment', 'Hailegarment Production'),
        ('kera_ifoam', 'Kera I Foam Production')
    ], string='Manufacturing Site')
    
    # Picking type field that will be automatically selected based on manufacturing site
    picking_type_id = fields.Many2one('stock.picking.type', string='Operation Type', 
                                      domain=[('code', '=', 'mrp_operation')])

    shape = fields.Selection([
        ('Rectangular', 'Rectangular'),
        ('Circular', 'Circular'),
        ('Triangular', 'Triangular')
    ], 'Shape', default='Rectangular')
    length = fields.Float(string="Length", default=1.0, digits=(16, 2))
    width = fields.Float(string="Width", default=1.0, digits=(16, 2))
    height = fields.Float(string="Height", default=1.0, digits=(16, 2))

    r_length = fields.Integer(string="R.", default=1)
    r_width = fields.Integer(string="R.", default=1)

    volume_price = fields.Float(string="Volume*Price")
    volume = fields.Float(string="Volume")
    foam_unit_price = fields.Float(string="Unit Price of Foam")
    fabric = fields.Boolean(string="Fabric", default=False)
    
    def action_confirm(self):
        """
        Override the standard action_confirm to create a single manufacturing order
        when a non-standard sale order is confirmed.
        """
        _logger.info(f"[SO-{self.name}] Starting confirmation of sales order")
        
        # First, ensure all order lines have the correct UoM to avoid category mismatch
        for line in self.order_line:
            if line.product_id and line.product_uom != line.product_id.uom_id:
                _logger.info(f"[SO-{self.name}] Adjusting UoM for product {line.product_id.display_name} from {line.product_uom.name} to {line.product_id.uom_id.name}")
                line.product_uom = line.product_id.uom_id
        
        # Only proceed with MO creation if this is a non-standard order
        if not self.non_standard:
            _logger.info(f"[SO-{self.name}] Not a non-standard order, skipping MO creation")
            return super(ExtendSale, self).action_confirm()
            
        _logger.info(f"[SO-{self.name}] Processing non-standard order with {len(self.order_line)} lines")
        
        # First confirm the order without creating MOs
        res = super(ExtendSale, self.with_context(bypass_mo_creation=True)).action_confirm()
        
        # Find or create a BoM for the main product
        main_product = None
        main_product_line = None
        
        # First, try to find a main product (one with a BoM or marked as storable)
        for line in self.order_line:
            if line.product_id and line.product_id.detailed_type == 'product':
                main_product = line.product_id
                main_product_line = line
                _logger.info(f"[SO-{self.name}] Found main product: {main_product.display_name}")
                break
        
        # If no main product found, use the first line
        if not main_product and self.order_line:
            main_product_line = self.order_line[0]
            main_product = main_product_line.product_id
            _logger.info(f"[SO-{self.name}] Using first product as main: {main_product.display_name}")
        
        if not main_product:
            _logger.error(f"[SO-{self.name}] No valid product found for MO creation")
            return res
        
        try:
            # Find or create a BoM for the main product
            bom = self.env['mrp.bom']._bom_find(
                main_product,
                company_id=self.company_id.id,
                bom_type='normal'
            ).get(main_product, self.env['mrp.bom'])
            
            if not bom:
                # Create a simple BoM if none exists
                _logger.info(f"[SO-{self.name}] Creating new BoM for {main_product.display_name}")
                bom = self.env['mrp.bom'].create({
                    'product_tmpl_id': main_product.product_tmpl_id.id,
                    'product_qty': 1,
                    'product_uom_id': main_product.uom_id.id,
                    'type': 'normal',
                    'company_id': self.company_id.id,
                })
            
            _logger.info(f"[SO-{self.name}] Using BoM: {bom.display_name} (ID: {bom.id})")
            
            # Create the manufacturing order
            mo_vals = {
                'product_id': main_product.id,
                'product_qty': main_product_line.product_uom_qty if main_product_line else 1.0,
                'product_uom_id': main_product.uom_id.id,
                'bom_id': bom.id,
                'origin': self.name,
                'company_id': self.company_id.id,
                'date_planned_start': fields.Datetime.now(),
                'sale_order_id': self.id,
                'sale_line_id': main_product_line.id if main_product_line else False,
                'isNOnStandard': True,
                # 'x_studio_manufacturing_site': self.manufacturing_site,
            }
            
            _logger.info(f"[SO-{self.name}] Creating manufacturing order")
            mo = self.env['mrp.production'].create(mo_vals)
            
            # Add all other products as raw materials to the MO
            component_count = 0
            for line in self.order_line:
                if line.product_id and line.product_id != main_product:
                    # Create a raw material move for each component
                    
                    self.env['stock.move'].create({
                        'production_id': mo.id,
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'name': line.name or line.product_id.name,
                        'location_id': mo.location_src_id.id,
                        'location_dest_id': mo.product_id.property_stock_production.id,
                        'raw_material_production_id': mo.id,
                        'state': 'draft',
                    })
                    component_count += 1
            
            _logger.info(f"[SO-{self.name}] Added {component_count} components to MO {mo.name}")
            
            # Confirm the manufacturing order
            mo.action_confirm()
            
            # Update all order lines with the created MO's moves
            if mo.move_raw_ids:
                move_ids = mo.move_raw_ids.ids
                for line in self.order_line:
                    line.write({'move_ids': [(6, 0, move_ids)]})
            
            _logger.info(f"[SO-{self.name}] Successfully created MO {mo.name} with {component_count} components")
            
        except Exception as e:
            _logger.error(f"[SO-{self.name}] Error creating manufacturing order: {str(e)}", exc_info=True)
            raise
            
        return res
    corner = fields.Boolean(string="Corner", default=False)
    # fabric_type = fields.Selection([
    #     ('Type1', 'Type 1'),
    #     ('Type2', 'Type 2'),
    # ], 'Foam Type', default='Type1', required_if_fabric=True)
    fabric_1 = fields.Many2one("product.product", string="Fabric", domain="[('products', '=', 'Fabric')]")
    fabric_2 = fields.Many2one("product.product", string="Fasha", domain="[('products', '=', 'Fasha')]")
    fabric_unit_price = fields.Float(string="H-Unit Price")
    fabric_unit_price_2 = fields.Float(string="V- Unit Price")

    fabric_size_1 = fields.Float(string='H-Size')
    fabric_size_2 = fields.Float(string='Fasha')

    fabric_total_1 = fields.Float(string='H-Fabric Total')
    fabric_total_2 = fields.Float(string='Fasha Total 2')

    tape_edge = fields.Boolean(string="Tape Edge", default=False)
    tape_edge_qty = fields.Float(string='Qty')
    tape_edge_unit_price = fields.Float(string='Unit Price')
    tape_edge_total = fields.Float(string='Tape Total')

    glue = fields.Boolean(string="Glue", default=False)
    glue_qty = fields.Float(string='Qty')
    glue_unit_price = fields.Float(string='Unit Price')

    glue_double = fields.Boolean(string='Double')
    glu_total = fields.Float(string='Glue Total')

    Seal = fields.Boolean(string="Seal", default=False)
    seal_qty = fields.Float(string='Qty')
    # seal_side = fields.Selection(
    #     [
    #         ('1 Sided', '1 Side'),
    #         ('2 Side', '2 Side'),
    #         ('3 Side', '3 Side'),
    #         ('4 Side', '4 Side')
    #     ], 'Number of Side', default='1 Sided'
    # )
    seal_type= fields.Many2one("product.product", string="Seal", domain="[('products', '=', 'Seal')]")
    seal_unit_price = fields.Float(string='Unit Price')
    seal_total = fields.Float(string='Seal Total')
    description = fields.Char(string='Description')

    parent_product = fields.Many2one("product.product", string="Product")

    packrise = fields.Boolean(string="Packrise", default=False)

    packrise_height = fields.Integer(string="Packrise Height", default=0)
    
    @api.onchange('manufacturing_site')
    def _onchange_manufacturing_site(self):
        """Automatically select picking type (operation type) based on manufacturing site selection"""
        if not self.manufacturing_site:
            self.picking_type_id = False
            return
            
        # Define the mapping of manufacturing sites to picking type names
        picking_type_mapping = {
            'dukem_foam': 'Foam Quilting Production',
            'dukem_bonded': 'Bonded Quilting Production',
            'hailegarment': 'Hailegarment Ifoam Production',
            'kera_ifoam': 'Kera Ifoam Manufacturing'
        }
        
        picking_type_name = picking_type_mapping.get(self.manufacturing_site)
        if picking_type_name:
            # Search for the picking type by name
            picking_type = self.env['stock.picking.type'].search([
                ('name', '=', picking_type_name),
                ('code', '=', 'mrp_operation')
            ], limit=1)
            
            if picking_type:
                self.picking_type_id = picking_type
                _logger.info(f"[SO-{self.name}] Automatically selected picking type: {picking_type.name} for manufacturing site: {self.manufacturing_site}")
            else:
                # If exact match not found, try partial match
                picking_type = self.env['stock.picking.type'].search([
                    ('name', 'ilike', picking_type_name),
                    ('code', '=', 'mrp_operation')
                ], limit=1)
                
                if picking_type:
                    self.picking_type_id = picking_type
                    _logger.info(f"[SO-{self.name}] Automatically selected picking type (partial match): {picking_type.name} for manufacturing site: {self.manufacturing_site}")
                else:
                    self.picking_type_id = False
                    _logger.warning(f"[SO-{self.name}] No picking type found for manufacturing site: {self.manufacturing_site}")
                    # Optionally show a warning to the user
                    return {
                        'warning': {
                            'title': 'Operation Type Not Found',
                            'message': f'No operation type found for {picking_type_name}. Please create the operation type or select one manually.'
                        }
                    }
    
    def clear(self):
        self.height = 1
        self.width = 1
        self.length = 1
        self.foam_unit_price = 0
        self.fabric_unit_price = 0
        self.description=''
        self.packrise = False
        self.packrise_height = 0
        self.r_length = 1
        self.r_width = 1
        self.value = None
        self.volume =0
        self.volume_price = 0
        self.parent_product = None

        self.seal_unit_price = ''
        self.seal_qty = 1
        self.seal_total = None

        self.fabric = False
        self.fabric_1 = None
        self.fabric_2 = None
        self.fabric_size_1 = 0
        self.fabric_size_2 = 0
        self.fabric_total_1 =0
        self.fabric_total_2 = 0
        
        self.tape_edge=False
        self.tape_edge_qty=1
        self.tape_edge_total = 0
    @api.onchange('value')
    def _onchange_value(self):
        self.foam_unit_price = self.value.list_price

    @api.onchange('seal_type')
    def _onchange_seal(self):
        self.change_seal_data()

    @api.onchange('Seal')
    def _onchange_seal(self):
        if self.Seal:
            self.seal_qty = self.length / 100
    @api.onchange('tape_edge')
    def _onchange_tape(self):
        self.change_tape_edge_data()

    @api.onchange('glue')
    def _onchange_glue(self):
        self.change_glue_data()

    @api.onchange('fabric')
    def _onchange_fabric(self):
        length_m = int(self.length) / 100
        width_m = int(self.width) / 100
        # self.fabric_size_1 = (length_m * width_m * 2)
        # self.fabric_size_1 = (length_m  * 2)
        self.fabric_size_2 = (length_m * 2) + (width_m * 2)
        self.fabric_size_1 = ((self.width + 4)/100)* 2 

    @api.onchange('fabric_1')
    def _onchange_fabric(self):
        self.change_fabric_data()

    @api.onchange('fabric_2')
    def _onchange_fasha(self):
        self.change_fasha_data()

    def change_tape_edge_data(self):
        """Updated tape edge calculation based on BRD"""
        if not self.tape_edge:
            return
            
        tape_product = self.env['product.product'].search([('name', '=', 'Tape Edge')])
        if not tape_product:
            self.tape_edge = False
            raise UserError('No Tape edge Product detected, please create a product called Tape Edge')
            
        self.tape_edge_qty = self.calculate_tape_edge_quantity(self.r_length, self.r_width)
        self.tape_edge_unit_price = tape_product[0].list_price
        self.tape_edge_total = self.tape_edge_qty * self.tape_edge_unit_price

    def change_glue_data(self):
        """
        Updated glue calculation based on PDF specification.
        Uses glue-specific rounding (independent of foam type).
        """
        if not self.glue:
            return

        glue_product = self.env['product.product'].search([('name', '=', 'Glue')])
        if not glue_product:
            self.glue = False
            raise UserError('No Glue Product detected, please create a product called Glue')

        # Use ACTUAL length and width (not r_length/r_width)
        # The calculate_glue_quantity method will apply its own PDF-compliant rounding
        self.glue_qty = self.calculate_glue_quantity(self.length, self.width)
        self.glue_unit_price = glue_product[0].list_price

        if self.glue_double:
            self.glu_total = self.glue_qty * self.glue_unit_price * 2
            self.glue_qty = self.glue_qty * 2
        else:
            self.glu_total = self.glue_qty * self.glue_unit_price

    def change_seal_data(self):
        """Updated seal calculation based on BRD"""
        if not self.Seal or not self.seal_type:
            return
            
        self.seal_qty = self.calculate_seal_quantity(self.r_length, self.r_width)
        self.seal_unit_price = self.seal_type.lst_price
        self.seal_total = self.seal_qty * self.seal_unit_price

    def change_fabric_data(self):
        """Updated fabric calculation based on BRD"""
        if not self.fabric_1:
            return
            
        # Calculate length in meters
        length_m = self.r_length / 100
        
        # Set fabric_size_1 to (length in meters) * 2
        # self.fabric_size_1 = length_m * 2

        self.fabric_size_1 = ((self.width + 4)/100)* 2 

        self.fabric_unit_price = self.fabric_1.lst_price
        self.fabric_total_1 = self.fabric_size_1 * self.fabric_unit_price
        
        # Auto-select fasha based on height
        self._auto_select_fasha()

    def change_fasha_data(self):
        """Updated fasha calculation based on BRD"""
        if not self.fabric_2:
            return
            
        # Calculate fasha size based on BRD
        length_m = self.r_length / 100
        width_m = self.r_width / 100
        fash_satin = (length_m * 2) + (width_m * 2)
        
        # Apply corner adjustment per BRD
        if self.corner:
            fash_satin += 0.12
            
        self.fabric_size_2 = fash_satin
        self.fabric_unit_price_2 = self.fabric_2.lst_price
        self.fabric_total_2 = self.fabric_size_2 * self.fabric_unit_price_2

    def _auto_select_fasha(self):
        """Auto-select fasha based on height"""
        if not self.fabric_1:
            return
            
        height_category = self.find_heigth(self.height)
        fashas = self.fabric_1.fasha_ids
        
        if fashas:
            # Try to find matching fasha based on height
            for fasha in fashas:
                if hasattr(fasha, 'height_category') and fasha.height_category == height_category:
                    self.fabric_2 = fasha
                    break
            # If no match found, use first available fasha
            if not self.fabric_2 and fashas:
                self.fabric_2 = fashas[0]

    @api.onchange('height', 'foam_unit_price', 'packrise_height',
                  'packrise', 'seal_type', 'fabric_total_1',
                  'fabric_total_2', 'seal_total', 'glu_total', 'glue_double',
                  'tape_edge_total', 'Seal', 'glue', 'tape_edge', 'fabric',
                  'corner', 'shape', 'value')
    def _onchange_dimention(self):
        if not self.non_standard:
            return
            
        # Calculate volume using rounded dimensions
        length_m = self.r_length / 100
        width_m = self.r_width / 100
        height_m = self.height / 100  # Note: height doesn't have a rounded field
        
        # Calculate volume in cubic meters using rounded dimensions
        volume = length_m * width_m * height_m
        
        # Handle packrise calculation
        if self.packrise:
            # Halve the volume for storage when packrise is True
            volume = volume / 2
            
            # Calculate price volume with packrise height if available
            if self.packrise_height and self.packrise_height > 0:
                price_height_m = ((self.height + self.packrise_height) / 100)/2
                _logger.info("packrise test this is from teddy  to see half value: %s", price_height_m)

                volume = length_m * width_m * price_height_m
               
            else:
                volume = volume
            
            self.volume = volume
            self.volume_price = volume * self.foam_unit_price
        else:
            self.volume = volume
            self.volume_price = volume * self.foam_unit_price

        # Update fabric calculations
        if self.fabric:
            self.change_fabric_data()
            self.change_fasha_data()
        
        # Update other calculations
        self.change_tape_edge_data()
        self.change_seal_data()
        self.change_glue_data()
        
        # Calculate total
        total = self.volume_price
        if self.fabric:
            total += self.fabric_total_1 + self.fabric_total_2
        if self.Seal:
            total += self.seal_total
        if self.tape_edge:
            total += self.tape_edge_total
        if self.glue:
            total += self.glu_total
            
        # Generate description
        foam_type = self.value.products if self.value else "Unknown"
        name = f"{self.shape} {foam_type} {self.length}x{self.width}x{self.height}"
        if self.packrise:
            name += f" ({self.packrise_height})"
        if self.fabric:
            name += f" {self.fabric_1.display_name if self.fabric_1 else ''}"
        if not self.shape == 'Rectangular':
            name += f" {self.shape}"
        if self.tape_edge:
            name += " TapedEdge"
            
        self.description = name
  
    def calculate_and_save(self):
        print("beggining to calculate the total price")
        if not self.parent_product:
            raise UserError('PLease select the parent product')
        total = self.volume_price
        if (self.fabric):
            print(total)
            print(self.fabric_total_2)
            print(self.fabric_total_1)
            total = float(total) + float(self.fabric_total_2)
            total = float(total) + float(self.fabric_total_1)
        if (self.Seal):
            total = total + self.seal_total
        if (self.tape_edge):
            total = total + self.tape_edge_total
        if self.glue:
            total = total + self.glu_total
        try:
            self.create_variant_and_save(total)
        except Exception as e:
            print(e)
            self.create_product_and_add_order_line(total)

    def find_product_add_order_line(self, total, attribute):
        order_lines = self.order_line
        for product in order_lines:
            if product.price_unit == total:
                if product.product_tmpl_id == self.parent_product.product_tmpl_id:
                    product.product_uom_qty += 1
                    return True
        return False

    def create_variant_and_save(self, final_price):
        # Simplified approach - just create a new product directly
        # Get UoM for PCs - use search instead of ref to avoid external ID issues
        uom_pc = self.env['uom.uom'].search([('name', '=', 'Units')], limit=1)
        if not uom_pc:
            uom_pc = self.env['uom.uom'].search([], limit=1)  # Fallback to first UoM
        
        # Create product name according to BRD format
        foam_type = self.value.products if self.value else "Unknown"
        parent_name = self.parent_product.name if self.parent_product else "Unknown"
        product_name = f"{self.shape} {parent_name} {self.length}x{self.width}x{self.height}"
        
        # Add packrise height if packrise is enabled
        if self.packrise and self.packrise_height:
            product_name += f" ({self.packrise_height})"

        if self.fabric:
            product_name += f" {self.fabric_1.display_name if self.fabric_1 else ''}"

            # Get MTO and Manufacture routes using XML IDs for reliability
        route_ids = []
        try:
            mto_route = self.env.ref('stock.route_warehouse0_mto', raise_if_not_found=False)
            if mto_route:
                route_ids.append(mto_route.id)
        except:
            pass
        
        try:
            manufacture_route = self.env.ref('mrp.route_warehouse0_manufacture', raise_if_not_found=False)
            if manufacture_route:
                route_ids.append(manufacture_route.id)
        except:
            pass
        
        # Create product with proper default settings
        product_vals = {
            "name": product_name,
            "list_price": final_price,
            "type": "product",  # Storable
            "purchase_ok": True,
            "sale_ok": True,
            "route_ids": [(6, 0, route_ids)] if route_ids else [],
        }
        
        # Add UoM if found
        if uom_pc:
            product_vals.update({
                "uom_id": uom_pc.id,  # Unit of Measurement: PCs
                "uom_po_id": uom_pc.id,  # Purchase Unit of Measurement: PCs
            })
        
        # Create the product
        product_obj = self.env['product.product'].create(product_vals)
        
        # Update the product template name to remove the CUST- prefix if it exists
        clean_name = product_name  # This is the clean name without the CUST- prefix
        if product_obj.product_tmpl_id.name != clean_name:
            product_obj.product_tmpl_id.write({'name': clean_name})
        
        # Create Bill of Materials
        self._create_bom_for_product(product_obj)
        
        # Add to order line with clean names
        val = {
            "product_id": product_obj.id,
            "product_template_id": product_obj.product_tmpl_id.id,
            "order_id": self.id,
            'name': clean_name,  # Use the clean name without the CUST- prefix
            'price_unit': product_obj.list_price,
            'product_uom_qty': 1,
            'customer_lead': 30,
            'company_id': self.company_id.id,
        }
        order_line_object = self.env['sale.order.line'].create(val)
        self.write({'order_line': [(4, order_line_object.id)]})

    def create_product_and_add_order_line(self, final_price):
        # Get UoM for PCs - use search instead of ref to avoid external ID issues
        uom_pc = self.env['uom.uom'].search([('name', '=', 'Units')], limit=1)
        if not uom_pc:
            uom_pc = self.env['uom.uom'].search([], limit=1)  # Fallback to first UoM
        
        # Create product name according to BRD format - using parent product name
        parent_name = self.parent_product.name if self.parent_product else "Unknown"
        product_name = f"{self.shape} {parent_name} {self.length}x{self.width}x{self.height}"
        
        # Add packrise height if packrise is enabled
        if self.packrise and self.packrise_height:
            product_name += f" ({self.packrise_height})"

        # if self.fabric:
        #     product_name += f" {self.fabric_1.display_name if self.fabric_1 else ''}"

        if self.fabric_1:
            product_name = f"{self.fabric_1.display_name} {product_name}"

        
        # Create a unique reference code with company prefix
        # timestamp = fields.Datetime.now().strftime('%Y%m%d%H%M%S')
        # default_code = f"CUST-{self.company_id.id}-{timestamp}"

        # Check if product with same name already exists
        existing_product = self.env['product.product'].search([
            ('name', '=', product_name),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        if existing_product:
            # Use existing product
            product_obj = existing_product
        else:
            # Get MTO and Manufacture routes using XML IDs for reliability
            route_ids = []
            try:
                mto_route = self.env.ref('stock.route_warehouse0_mto', raise_if_not_found=False)
                if mto_route:
                    route_ids.append(mto_route.id)
            except:
                pass
            
            try:
                manufacture_route = self.env.ref('mrp.route_warehouse0_manufacture', raise_if_not_found=False)
                if manufacture_route:
                    route_ids.append(manufacture_route.id)
            except:
                pass
            
            # Create product with proper default settings
            product_vals = {
                "name": product_name,
                # "default_code": default_code,  # Add unique reference with company prefix
                "list_price": final_price,
                "categ_id": 1197,
                "type": "product",  # Storable
                "purchase_ok": True,
                "sale_ok": True,
                "route_ids": [(6, 0, route_ids)] if route_ids else [],
                "company_id": self.company_id.id,  # Explicitly set company
            }
            
            # Add UoM if found
            if uom_pc:
                product_vals.update({
                    "uom_id": uom_pc.id,  # Unit of Measurement: PCs
                    "uom_po_id": uom_pc.id,  # Purchase Unit of Measurement: PCs
                })
            
            product_obj = self.env['product.product'].create(product_vals)
            
            # Create Bill of Materials
            self._create_bom_for_product(product_obj)
        
        # Add to order line
        val = {
            "product_id": product_obj.id,
            "product_template_id": product_obj.product_tmpl_id.id,
            "order_id": self.id,
            'name': product_obj.name,
            # 'price_unit': product_obj.list_price,
            'price_unit': self.final_total_all,
            'product_uom_qty': 1,
            'customer_lead': 30,
            'company_id': self.company_id.id,
        }
        order_line_object = self.env['sale.order.line'].create(val)
        self.write({'order_line': [(4, order_line_object.id)]})

    def _create_bom_for_product(self, product_obj):
        """Create Bill of Materials for the created product"""
        bom_lines = []
        
        # Get UoM references safely with categories
        uom_unit = self.env['uom.uom'].search([('name', '=', 'Units'), ('category_id.name', '=', 'Unit')], limit=1)
        uom_m3 = self.env['uom.uom'].search([('name', '=', 'm³'), ('category_id.name', '=', 'Volume')], limit=1)
        uom_kg = self.env['uom.uom'].search([('name', '=', 'kg'), ('category_id.name', '=', 'Weight')], limit=1)
        uom_meter = self.env['uom.uom'].search([('name', '=', 'm'), ('category_id.name', '=', 'Length')], limit=1)
        
        # Fallback to first available UoM in category if not found
        if not uom_unit:
            uom_unit = self.env['uom.uom'].search([('category_id.name', '=', 'Unit')], limit=1) or self.env['uom.uom'].search([], limit=1)
        if not uom_m3:
            uom_m3 = self.env['uom.uom'].search([('category_id.name', '=', 'Volume')], limit=1) or uom_unit
        if not uom_kg:
            uom_kg = self.env['uom.uom'].search([('category_id.name', '=', 'Weight')], limit=1) or uom_unit
        if not uom_meter:
            uom_meter = self.env['uom.uom'].search([('category_id.name', '=', 'Length')], limit=1) or uom_unit
        
        # 1. Foam (selected by user) - Quantity based on volume
        if self.parent_product:
            foam_qty = self.volume  # Volume in m³
            bom_lines.append((0, 0, {
                'product_id': self.parent_product.id,
                'product_uom_id': uom_m3.id if uom_m3 else uom_unit.id,
                'product_qty': self.volume,
            }))
        
        # 2. Glue - Quantity based on volume or predefined
        if self.glue:
            glue_product = self.env['product.product'].search([('name', '=', 'Glue')])
            if not glue_product:
                glue_product = self.env['product.product'].search([('name', 'ilike', 'Glue')], limit=1)
            
            if glue_product:
                glue_qty = self.glue_qty if hasattr(self, 'glue_qty') else (self.volume / 1)  # 1 kg per m³
                bom_lines.append((0, 0, {
                    'product_id': glue_product[0].id,
                    'product_uom_id': uom_kg.id if uom_kg else uom_unit.id,
                    'product_qty': glue_qty,
                }))
        
        # 3. Seal - Quantity based on length or predefined
        if self.Seal and self.seal_type:
            # Get the seal product's UoM instead of forcing meters
            seal_product = self.env['product.product'].browse(self.seal_type.id)
            seal_uom = seal_product.uom_id or uom_unit
            
            # Convert quantity to seal's UoM if needed
            seal_qty = self.seal_qty if hasattr(self, 'seal_qty') else (self.length / 100)  # Default in meters
            
            # If seal's UoM is not meters, convert the quantity
            if seal_uom != uom_meter and uom_meter and seal_uom.category_id == uom_meter.category_id:
                seal_qty = uom_meter._compute_quantity(seal_qty, seal_uom)
            
            bom_lines.append((0, 0, {
                'product_id': self.seal_type.id,
                'product_uom_id': seal_uom.id,
                'product_qty': seal_qty,
            }))
        
        # 4. Tape Edge - Quantity based on perimeter
        if self.tape_edge:
            tape_product = self.env['product.product'].search([('name', '=', 'Tape Edge')])
            if not tape_product:
                tape_product = self.env['product.product'].search([('name', 'ilike', 'Tape')], limit=1)
            
            if tape_product:
                tape_qty = self.tape_edge_qty if hasattr(self, 'tape_edge_qty') else (((self.length / 100 * 2) + (self.width / 100 * 2)) * 2)
                bom_lines.append((0, 0, {
                    'product_id': tape_product[0].id,
                    'product_uom_id': uom_meter.id if uom_meter else uom_unit.id,
                    'product_qty': tape_qty,
                }))
        
        # 5. Fabric components
        if self.fabric and self.fabric_1:
            fabric_qty = self.fabric_size_1 if hasattr(self, 'fabric_size_1') else ((self.r_length / 100) * 2)
            bom_lines.append((0, 0, {
                'product_id': self.fabric_1.id,
                'product_uom_id': uom_meter.id if uom_meter else uom_unit.id,
                'product_qty': fabric_qty,
            }))
        
        if self.fabric and self.fabric_2:
            fasha_qty = self.fabric_size_2 if hasattr(self, 'fabric_size_2') else ((self.r_length / 100 * 2) + (self.r_width / 100 * 2))
            bom_lines.append((0, 0, {
                'product_id': self.fabric_2.id,
                'product_uom_id': uom_meter.id if uom_meter else uom_unit.id,
                'product_qty': fasha_qty,
            }))
        
        # Always use component's default UoM for all components
        for i, (_, _, line_vals) in enumerate(bom_lines):
            try:
                component = self.env['product.product'].browse(line_vals.get('product_id'))
                if component:
                    original_uom = self.env['uom.uom'].browse(line_vals.get('product_uom_id', component.uom_id.id))
                    if original_uom.id != component.uom_id.id:
                        _logger.info(f"[BOM] Using default UoM for {component.display_name}: "
                                  f"{component.uom_id.name} (ID: {component.uom_id.id}) "
                                  f"instead of {original_uom.name} (ID: {original_uom.id})")
                        line_vals['product_uom_id'] = component.uom_id.id
            except Exception as e:
                _logger.error(f"[BOM] Error setting default UoM for component: {str(e)}")
                continue
                
        # Create BOM if we have components
        if bom_lines:
            _logger.info(f"[BOM] Starting BOM creation for product {product_obj.display_name} (ID: {product_obj.id})")
            
            # Log UoM information for the main product
            try:
                _logger.info(f"[BOM] Product UoM: {product_obj.uom_id.name} (ID: {product_obj.uom_id.id}, Category: {product_obj.uom_id.category_id.name})")
            except Exception as e:
                _logger.error(f"[BOM] Error getting product UoM: {str(e)}")
            
            # Log UoM information for all components
            for i, (_, _, line) in enumerate(bom_lines, 1):
                try:
                    component = self.env['product.product'].browse(line.get('product_id'))
                    _logger.info(f"[BOM] Component {i}: {component.display_name} (ID: {component.id})")
                    _logger.info(f"[BOM]   - Component UoM: {component.uom_id.name} (Category: {component.uom_id.category_id.name})")
                    _logger.info(f"[BOM]   - Line UoM: {self.env['uom.uom'].browse(line.get('product_uom_id')).name if line.get('product_uom_id') else 'Not set'}")
                except Exception as e:
                    _logger.error(f"[BOM] Error logging component {i} info: {str(e)}")
            
            # Get picking type from sale order or use default
            try:
                if self.picking_type_id:
                    picking_type = self.picking_type_id
                    _logger.info(f"[BOM] Using picking type from sale order: {picking_type.display_name} (ID: {picking_type.id})")
                else:
                    picking_type = self.env['stock.picking.type'].search([
                        ('code', '=', 'mrp_operation'),
                        ('company_id', '=', self.company_id.id or self.env.company.id)
                    ], limit=1)
                    
                    # Fallback to default manufacturing picking type if not found
                    if not picking_type:
                        _logger.warning("[BOM] No specific picking type found for company, trying default")
                        picking_type = self.env.ref('mrp.picking_type_manufacturing', raise_if_not_found=False)
                        if picking_type:
                            _logger.info(f"[BOM] Using default picking type: {picking_type.display_name} (ID: {picking_type.id})")
            except Exception as e:
                _logger.error(f"[BOM] Error getting picking type: {str(e)}")
                picking_type = False
            
            try:
                # Log UoM validation before creating BOM
                if uom_unit:
                    _logger.info(f"[BOM] Final BOM UoM: {uom_unit.name} (ID: {uom_unit.id}, Category: {uom_unit.category_id.name})")
                else:
                    _logger.warning("[BOM] No UoM specified, using default UoM (ID: 1)")
                
                # Prepare BOM values with detailed logging
                bom_vals = {
                    'product_tmpl_id': product_obj.product_tmpl_id.id,
                    'product_id': product_obj.id,
                    'type': 'normal',
                    'product_qty': 1.0,
                    'product_uom_id': uom_unit.id if uom_unit else 1,
                    'bom_line_ids': bom_lines,
                    'company_id': self.company_id.id or self.env.company.id,
                }
                _logger.debug(f"[BOM] Prepared BOM values: {bom_vals}")
                
                # Log component UoM categories for validation
                for i, (_, _, line) in enumerate(bom_vals.get('bom_line_ids', []), 1):
                    try:
                        component = self.env['product.product'].browse(line.get('product_id'))
                        line_uom = self.env['uom.uom'].browse(line.get('product_uom_id'))
                        _logger.info(f"[BOM] Validating component {i} UoM:")
                        _logger.info(f"[BOM]   - Component: {component.display_name}")
                        _logger.info(f"[BOM]   - Component UoM: {component.uom_id.name} (Category: {component.uom_id.category_id.name})")
                        _logger.info(f"[BOM]   - Line UoM: {line_uom.name if line_uom else 'Not set'} (Category: {line_uom.category_id.name if line_uom else 'N/A'})")
                        
                        if line_uom and component.uom_id.category_id != line_uom.category_id:
                            _logger.error(f"[BOM] UoM CATEGORY MISMATCH for {component.display_name}:")
                            _logger.error(f"[BOM]   - Expected category: {component.uom_id.category_id.name}")
                            _logger.error(f"[BOM]   - Actual category: {line_uom.category_id.name}")
                            
                    except Exception as e:
                        _logger.error(f"[BOM] Error validating component {i} UoM: {str(e)}")
                        
            except Exception as e:
                _logger.error(f"[BOM] Error preparing BOM values: {str(e)}")
                raise
            
            # Add picking type if found
            if picking_type:
                bom_vals['picking_type_id'] = picking_type.id
            
            _logger.info(f"[BOM] Creating BOM for product {product_obj.display_name} with {len(bom_lines)} components")
            if picking_type:
                _logger.info(f"[BOM] Using picking type: {picking_type.display_name} (ID: {picking_type.id})")
            
            self.env['mrp.bom'].create(bom_vals)

    def _apply_foam_rounding_rules_length(self, value):
        """Foam rounding rules for length - BRD compliant"""
        if value <= 0:
            return value
        elif 0 < value <= 47:
            return value  # No rounding
        elif 48 <= value <= 50:
            return 50
        elif 51 <= value <= 55:
            return 55
        elif 56 <= value <= 60:
            return 60
        elif 61 <= value <= 65:
            return 65
        elif 66 <= value <= 75:
            return 75
        elif 76 <= value <= 80:
            return 80
        elif 81 <= value <= 100:
            return 100
        elif 101 <= value <= 120:
            return 120
        elif 121 <= value <= 150:
            return 150
        elif 151 <= value <= 160:
            return 160
        elif 161 <= value <= 190:
            return 190
        elif 191 <= value <= 200:
            return 200
        else:
            return value

    def _apply_foam_rounding_rules_width(self, value):
        """Foam rounding rules for width - BRD compliant"""
        if value <= 0:
            return value
        elif 0 < value <= 47:
            return value  # No rounding
        elif 48 <= value <= 50:
            return 50
        elif 51 <= value <= 55:
            return 55
        elif 56 <= value <= 60:
            return 60
        elif 61 <= value <= 65:
            return 65
        elif 66 <= value <= 75:
            return 75
        elif 76 <= value <= 80:
            return 80
        elif 81 <= value <= 100:
            return 100
        elif 101 <= value <= 120:
            return 120
        elif 121 <= value <= 150:
            return 150
        elif 151 <= value <= 160:
            return 160
        elif 161 <= value <= 180:
            return 180
        elif 181 <= value <= 190:
            return 190
        elif 191 <= value <= 200:
            return 200
        else:
            return value  # Above 200 not round number per BRD

    def _apply_bonded_rounding_rules_length(self, value):
        """Bonded rounding rules for length - BRD compliant"""
        if value <= 0:
            return value
        elif 0 < value <= 20:
            return value  # No rounding
        elif 21 <= value <= 30:
            return 30
        elif 31 <= value <= 40:
            return 40
        elif 41 <= value <= 50:
            return 50
        elif 51 <= value <= 65:
            return 65
        elif 66 <= value <= 75:
            return 75
        elif 76 <= value <= 80:
            return 80
        elif 81 <= value <= 100:
            return 100
        elif 101 <= value <= 130:
            return 130
        elif 131 <= value <= 150:
            return 150
        elif 151 <= value <= 160:
            return 160
        elif 161 <= value <= 200:
            return 200
        else:
            return value  # Above 200 not round number per BRD

    def _apply_bonded_rounding_rules_width(self, value):
        """Bonded rounding rules for width - BRD compliant"""
        if value <= 0:
            return value
        elif 0 < value <= 21:
            return value  # No rounding
        elif 21 <= value <= 30:
            return 30
        elif 31 <= value <= 40:
            return 40
        elif 41 <= value <= 50:
            return 50
        elif 51 <= value <= 65:
            return 65
        elif 66 <= value <= 75:
            return 75
        elif 76 <= value <= 80:
            return 80
        elif 81 <= value <= 100:
            return 100
        elif 101 <= value <= 130:
            return 130
        elif 131 <= value <= 150:
            return 150
        elif 151 <= value <= 160:
            return 160
        elif 161 <= value <= 180:
            return 180
        elif 181 <= value <= 190:
            return 190
        elif 191 <= value <= 200:
            return 200
        else:
            return value  # Above 200 not round number per BRD

    def calculate_fabric_sizes(self, length, width, height):
        """Calculate fabric sizes based on BRD reference table"""
        # Convert to meters for calculation
        length_m = length / 100
        width_m = width / 100
        height_m = height / 100
        
        # Upper and Bottom Satin calculation
        upper_bottom_satin = length_m * width_m * 2  # 2 sides
        
        # Fash Satin calculation (perimeter)
        fash_satin = (length_m * 2) + (width_m * 2)
        
        # Apply corner adjustment if needed
        if self.corner:
            fash_satin += 0.12
            
        return upper_bottom_satin, fash_satin

    # def calculate_glue_quantity(self, length, width):
    #     """Calculate glue quantity based on BRD size rules"""
    #     # BRD Glue calculation rules
    #     size = f"{length}x{width}"
        
    #     if length >= 200 and width >= 200:
    #         return 3.0
    #     elif length >= 200 and width >= 180:
    #         return 2.7
    #     elif length >= 190 and width >= 150:
    #         return 2.13
    #     elif length >= 190 and width >= 120:
    #         return 1.71
    #     else:
    #         # Default calculation: 1 kg per m³
    #         volume_m3 = (length * width * self.height) / 1000000
    #         return volume_m3

    def _apply_glue_rounding_length(self, value):
        """
        Glue-specific rounding for LENGTH - matches PDF specification exactly.
        This is separate from foam/bonded rounding and used ONLY for glue calculation.

        PDF Length Rounding Table (Page 1):
        21–30 → 30, 31–40 → 40, 41–50 → 50, 51–65 → 65, 66–75 → 75,
        76–80 → 80, 81–100 → 100, 101–120 → 120, 121–150 → 150,
        151–160 → 160, 161–190 → 190, 191–200 → 200
        """
        if value <= 0:
            return value
        elif 0 < value <= 20:
            return value  # No rounding for values ≤ 20
        elif 21 <= value <= 30:
            return 30
        elif 31 <= value <= 40:
            return 40
        elif 41 <= value <= 50:
            return 50
        elif 51 <= value <= 65:
            return 65
        elif 66 <= value <= 75:
            return 75
        elif 76 <= value <= 80:
            return 80
        elif 81 <= value <= 100:
            return 100
        elif 101 <= value <= 120:
            return 120
        elif 121 <= value <= 150:
            return 150
        elif 151 <= value <= 160:
            return 160
        elif 161 <= value <= 190:
            return 190
        elif 191 <= value <= 200:
            return 200
        else:
            return value  # No rounding for values > 200

    def _apply_glue_rounding_width(self, value):
        """
        Glue-specific rounding for WIDTH - matches PDF specification exactly.
        This is separate from foam/bonded rounding and used ONLY for glue calculation.

        PDF Width Rounding Table (Page 2):
        21–30 → 30, 31–40 → 40, 41–50 → 50, 51–65 → 65, 66–75 → 75,
        76–80 → 80, 81–100 → 100, 101–120 → 120, 121–150 → 150,
        151–160 → 160, 161–180 → 180, 181–190 → 190, 191–200 → 200
        """
        if value <= 0:
            return value
        elif 0 < value <= 20:
            return value  # No rounding for values ≤ 20
        elif 21 <= value <= 30:
            return 30
        elif 31 <= value <= 40:
            return 40
        elif 41 <= value <= 50:
            return 50
        elif 51 <= value <= 65:
            return 65
        elif 66 <= value <= 75:
            return 75
        elif 76 <= value <= 80:
            return 80
        elif 81 <= value <= 100:
            return 100
        elif 101 <= value <= 120:
            return 120
        elif 121 <= value <= 150:
            return 150
        elif 151 <= value <= 160:
            return 160
        elif 161 <= value <= 180:
            return 180
        elif 181 <= value <= 190:
            return 190
        elif 191 <= value <= 200:
            return 200
        else:
            return value  # No rounding for values > 200

    def calculate_glue_quantity(self, length, width):
        """
        Calculate glue quantity using formula from PDF specification:
        Glue Quantity = 0.75 × (Rounded Length in meters) × (Rounded Width in meters)

        The factor 0.75 represents the standard glue usage per square meter.

        Args:
            length (float): Actual length in cm (from self.length, not r_length)
            width (float): Actual width in cm (from self.width, not r_width)

        Returns:
            float: Glue quantity in kg
        """
        # Apply GLUE-SPECIFIC rounding (independent of foam type)
        rounded_length = self._apply_glue_rounding_length(length)
        rounded_width = self._apply_glue_rounding_width(width)

        # Convert centimeters to meters
        length_m = rounded_length / 100.0
        width_m = rounded_width / 100.0

        # Calculate surface area in square meters
        area_m2 = length_m * width_m

        # Calculate glue quantity: 0.75 kg per square meter
        glue_quantity = 0.75 * area_m2

        # Log calculation for verification
        _logger.info(
            "[GLUE CALC] Input: L=%.2fcm W=%.2fcm | Rounded: L=%.2fcm W=%.2fcm | "
            "Meters: L=%.2fm W=%.2fm | Area: %.4fm² | Glue Qty: %.4fkg (0.75kg/m²)",
            length, width, rounded_length, rounded_width,
            length_m, width_m, area_m2, glue_quantity
        )

        return glue_quantity

    # OLD METHOD - Kept for reference (can be removed after verification)
    # def calculate_glue_quantity_old(self, length, width):
    #     """OLD: Calculate glue quantity based on width thresholds"""
    #     if width >= 200:
    #         return 3.0
    #     elif width >= 180:
    #         return 2.7
    #     elif width >= 150:
    #         return 2.13
    #     elif width < 150:
    #         return 1.71
    #     else:
    #         volume_m3 = (length * width * self.height) / 1000000
    #         return volume_m3

    def calculate_seal_quantity(self, length, width):
        """Calculate seal quantity based on BRD rules"""
        # If length is greater than width, use length
        # If width is greater than length, use width
        if length > width:
            return length / 100  # Convert to meters
        else:
            return width / 100  # Convert to meters

    def calculate_tape_edge_quantity(self, length, width):
        """Calculate tape edge quantity based on BRD formula"""
        # Formula: ((length/100)*2 + (width/100)*2)*2
        length_m = length / 100
        width_m = width / 100
        perimeter = (length_m * 2) + (width_m * 2)
        return perimeter * 2

    @api.onchange('length')
    def _onchange_length(self):
        """Apply correct rounding rules to length in real-time based on foam type"""
        if self.length and self.length > 0:
            foam_type = self.value.products if self.value else None
            if foam_type == 'Bonded':
                self.r_length = self._apply_bonded_rounding_rules_length(self.length)
            else:
                self.r_length = self._apply_foam_rounding_rules_length(self.length)

    @api.onchange('width')
    def _onchange_width(self):
        """Apply correct rounding rules to width in real-time based on foam type"""
        if self.width and self.width > 0:
            foam_type = self.value.products if self.value else None
            if foam_type == 'Bonded':
                self.r_width = self._apply_bonded_rounding_rules_width(self.width)
            else:
                self.r_width = self._apply_foam_rounding_rules_width(self.width)

    def convert_length(self, length):
        """Updated convert_length method using the new rounding rules"""
        print('this is length', length)
        if length <= 0:
            raise UserError('Length can not be 0 or less')
        return self._apply_foam_rounding_rules_length(length)

    def convert_width(self, width):
        """Updated convert_width method using the new rounding rules"""
        print('this is width', width)
        if width <= 0:
            raise UserError('Width can not be 0 or less')
        return self._apply_foam_rounding_rules_width(width)

    def find_heigth(self, height):
        print('this is width', height)
        if height <= 0:
            return UserError('Value can not be 0 or less')
        elif 0 < height <= 6:
            return 6
        elif 6 < height <= 12:
            return 12
        elif 12 < height <= 16:
            return 16
        elif 16 < height <= 20:
            return 20
        elif 20 < height <= 24:
            return 24
        else:
            return 24
    def convert_width_for_bonded(self, width):
        print('this is width', width)
        if width <= 0:
            return UserError('Width can not be 0 or less')
        elif 0 < width <= 0.20:
            return width
        elif 0.21 < width <= 0.30:
            return 0.30
        elif 0.30 < width <= 0.40:
            return 0.40
        elif 0.40 < width <= 0.50:
            return 0.50
        elif 0.50 < width <= 0.65:
            return 0.65
        elif 0.65 < width <= 0.75:
            return 0.75
        elif 0.75 < width <= 0.80:
            return 0.80
        elif 0.80 < width <= 1.00:
            return 1.00
        elif 1 < width <= 1.30:
            return 1.30
        elif 1.30 < width <= 1.50:
            return 1.50
        elif 1.50 < width <= 1.60:
            return 1.60
        elif 1.60 < width <= 1.80:
            return 1.80
        elif 1.80 < width <= 1.90:
            return 1.90
        elif 1.90 < width <= 2.00:
            return 2.00
        else:
            return width

    def convert_width_for_foam(self, width):
        print('this is width', width)
        if width <= 0:
            return UserError('Width can not be 0 or less')
        elif 0 < width <= 0.47:
             return width  # No rounding
        elif 0.48 <= width <= 0.50:
              return 0.50
        elif 0.51 <= width <= 0.55:
              return 0.55
        elif 0.56 <= width <= 0.60:
              return 0.60
        elif 0.61 <= width <= 0.65:
              return 0.65
        elif 0.66 <= width <= 0.75:
              return 0.75
        elif 0.76 <= width <= 0.80:
               return 0.80
        elif 0.81 <= width <= 1.00:
               return 1.00
        elif 1.01 <= width <= 1.20:
               return 1.20
        elif 1.21 <= width <= 1.50:
               return 1.50
        elif 1.51 <= width <= 1.60:
               return 1.60
        elif 1.61 <= width <= 1.80:
               return 1.80
        elif 1.81 <= width <= 1.90:
               return 1.90
        elif 1.91 <= width <= 2.00:
               return 2.00
        else:
              return width


    def convert_height_for_bonded(self, height):
        print('this is height', height)
        if height <= 0:
            return UserError('Height can not be 0 or less')
        

    def convert_length_for_bonded(self, length):
        print('this is length', length)
        if length <= 0:
            return UserError('Length can not be 0 or less')
        elif 0 < length <= 0.20:
            return length
        elif 0.21 < length <= 0.30:
            return 0.30
        elif 0.30 < length <= 0.40:
            return 0.40
        elif 0.40 < length <= 0.50:
            return 0.50
        elif 0.50 < length <= 0.65:
            return 0.65
        elif 0.65 < length <= 0.75:
            return 0.75
        elif 0.75 < length <= 0.80:
            return 0.80
        elif 0.80 < length <= 1.00:
            return 1.00
        elif 1 < length <= 1.30:
            return 1.30
        elif 1.30 < length <= 1.50:
            return 1.50
        elif 1.50 < length <= 1.60:
            return 1.60
        elif 1.60 < length <= 2.00:
            return 2.00
        else:
            return length

    def convert_length_for_foam(self, length):
        print('this is length', length)
        
        if length <= 0:
             raise UserError("Length must be greater than 0")
        elif 0 < length <= 0.47:
                return length  # No rounding
        elif 0.48 <= length <= 0.50:
             return 0.50
        elif 0.51 <= length <= 0.55:
              return 0.55
        elif 0.56 <= length <= 0.60:
              return 0.60
        elif 0.61 <= length <= 0.65:
              return 0.65
        elif 0.66 <= length <= 0.75:
              return 0.75
        elif 0.76 <= length <= 0.80:
              return 0.80
        elif 0.81 <= length <= 1.00:
              return 1.00
        elif 1.01 <= length <= 1.20:
              return 1.20
        elif 1.21 <= length <= 1.50:
              return 1.50
        elif 1.51 <= length <= 1.60:
              return 1.60
        elif 1.61 <= length <= 1.90:
              return 1.90
        elif 1.91 <= length <= 2.00:
              return 2.00
        else:
             return length
