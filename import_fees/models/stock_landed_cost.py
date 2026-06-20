from collections import defaultdict

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


import collections
import logging
from collections import namedtuple
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_round


def mynamedtuple(typename, field_names, defaults=()):
    T = namedtuple(typename, field_names)
    T.__new__.__defaults__ = defaults
    return T


def round_tariff(value):
    return value #float_round(value, precision_digits=2)

def round_total(value):
    return value #float_round(value, precision_digits=2)

class ReceivedProductLine(models.Model):
    _name = 'import_fees.received.product.line'
    _description = 'Received Product Line'
    # ==== Business fields ====
    landed_costs_id = fields.Many2one('stock.landed.cost', 'Landed Cost')
    move_id = fields.Many2one('stock.move', 'Stock Move', readonly=True)
    quantity = fields.Float(string='Quantity',
                            default=1.0, digits=(14, 4))
    price_unit = fields.Monetary(string='Unit Price', store=True, readonly=True,
                                 currency_field='currency_id')
    price_total = fields.Monetary(string='Total', store=True, readonly=True,
                                  currency_field='currency_id')
    local_price_total = fields.Monetary(string='Local Currency Total', store=True, readonly=True,
                                        currency_field='local_currency_id')
    currency_id = fields.Many2one('res.currency', string='Vendor Currency', required=True)
    currency_rate = fields.Float('Currency Rate', related='currency_id.rate', readonly=True)
    local_currency_id = fields.Many2one(related='landed_costs_id.currency_id', string='Local Currency', readonly=True,
                                        store=True)
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict', readonly=True)
    hs_code_id = fields.Many2one('import_fees.harmonized_code', string="HS Code", store=True, readonly=True,
                                 compute='_compute_hscode')

    @api.depends('product_id')
    def _compute_hscode(self):
        for elm in self:
            elm.hs_code_id = elm.product_id.search_harmonized_code_id()


class AdjustmentLines(models.Model):
    _inherit = 'stock.valuation.adjustment.lines'
    cost_line_product_id = fields.Many2one(related='cost_line_id.product_id', string='Cost', readonly=True)


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'
    amount_local_currency = fields.Monetary('Value in local currency', currency_field='currency_id', default=0.0,
                                            store=True,
                                            readonly=True, compute='_compute_amount_local_currency')
    vendor_bill_ids = fields.Many2many('account.move', 'stock_landed_cost_vendor_bill_rel', 'landed_cost_id',
                                       'vendor_bill_id', string='Vendor Bills', copy=False,
                                       domain=[('move_type', '=', 'in_invoice')])
    stevedoring = fields.Monetary('Stevedoring', currency_field='currency_id', default=0.0)
    demurrage = fields.Monetary('Demurrage', currency_field='currency_id', default=0.0)
    transport = fields.Monetary('Transport', currency_field='currency_id', default=0.0)
    storage = fields.Monetary('Storage', currency_field='currency_id', default=0.0)
    bank = fields.Monetary('Bank charges', currency_field='currency_id', default=0.0)
    miscellaneous = fields.Monetary('Miscellaneous', currency_field='currency_id', default=0.0)
    royalty_fee = fields.Monetary('Royalty fee', currency_field='currency_id', default=0.0)
    freight = fields.Monetary('Freight', currency_field='currency_id', default=0.0)
    clearance = fields.Monetary('Clearance', currency_field='currency_id', default=0.0)
    transit = fields.Monetary('Transit', currency_field='currency_id', default=0.0)
    insurance = fields.Monetary('Insurance', currency_field='currency_id', default=0.0)
    shipping = fields.Monetary('DHL/Fedex/UPS...', currency_field='currency_id', default=0.0)
    other = fields.Monetary('Other', currency_field='currency_id', default=0.0)
    royalty_fee_info = fields.Monetary('Royalty fee info', currency_field='currency_id', default=0.0)
    declared_value = fields.Monetary('Declared Value', currency_field='currency_id', default=0.0, readonly=True, compute='_compute_declared_value')
    customs_value = fields.Monetary('Total Duty', currency_field='currency_id', default=0.0, readonly=True, store=True,
                                    compute='_compute_customs_value')
    customs_vat_value = fields.Monetary('Customs VAT', currency_field='currency_id', default=0.0, readonly=True,
                                        compute='_compute_vat_value')
    total_customs_value = fields.Monetary('Total Customs Value', currency_field='currency_id', default=0.0,
                                          compute='_compute_total_customs_value')
    total_landed_cost = fields.Monetary('Total Landed Cost', currency_field='currency_id', default=0.0,
                                        compute='_compute_total_landed_cost')
    received_products_ids = fields.One2many('import_fees.received.product.line',
                                            compute='_compute_received_products_ids',
                                            inverse="_none", readonly=True, store=True, inverse_name='landed_costs_id', copy=False)
    customs_fees_ids = fields.One2many('import_fees.customs_fees', inverse_name='landed_costs_id', copy=False)
    create_landed_bill = fields.Boolean('Create Shipping Bill', compute='_compute_create_landed_bill')
    valuation_adjustment_lines = fields.One2many(
        'stock.valuation.adjustment.lines', 'cost_id', 'Valuation Adjustments',
        context={'group_by': ['product_id']}
    )
    
    @api.onchange('picking_ids')
    def _onchange_picking_ids_vendor_bills(self):
        if self.picking_ids:
            purchase_orders = self.env['purchase.order'].search([('name', 'in', self.picking_ids.mapped('origin'))])
            vendor_bills = purchase_orders.mapped('invoice_ids').filtered(lambda x: x.move_type == 'in_invoice')
            self.vendor_bill_ids = [(6, 0, vendor_bills.ids)]
        else:
            self.vendor_bill_ids = [(5, 0, 0)]  # Clear the vendor_bill_ids if no picking is selected
    
    @api.depends('received_products_ids','received_products_ids.local_price_total')
    def _compute_amount_local_currency(self):
        for record in self:
            record.amount_local_currency = sum([it.local_price_total for it in record.received_products_ids])
    
    def _compute_customs_bill_visible(self):
        for move in self:
            move.customs_bill_visible = self.env['ir.config_parameter'].sudo().get_param(
                'import_fees.customs_bill_visible', False)

    def _compute_shipping_bill_visible(self):
        for move in self:
            move.shipping_bill_visible = self.env['ir.config_parameter'].sudo().get_param(
                'import_fees.shipping_bill_visible', False)

    @api.depends('customs_fees_ids.amount')
    def _compute_customs_value(self):
        for record in self:
            fees_ids = record.customs_fees_ids
            if fees_ids and fees_ids[0].amount:
                record.customs_value = sum(it.amount for it in fees_ids)
                record.update_landed_cost_line('customs', record.customs_value, 'by_hscode')
            else:
                record.customs_value = 0.0
                record.update_landed_cost_line('customs', record.customs_value, 'by_hscode')

    @api.depends('customs_fees_ids.value')
    def _compute_declared_value(self):
        for record in self:
            fees_ids = record.customs_fees_ids
            if fees_ids:
                record.declared_value = sum(it.value for it in fees_ids)
            else:
                record.declared_value = 0.0

    @api.depends('customs_fees_ids.vat_value')
    def _compute_vat_value(self):
        for record in self:
            fees_ids = record.customs_fees_ids
            if fees_ids:
                record.customs_vat_value = sum([it.vat_value for it in fees_ids])
            else:
                record.customs_vat_value = 0.0

    @api.depends('customs_value', 'customs_vat_value')
    def _compute_total_customs_value(self):
        for record in self:
            record.total_customs_value = record.customs_value + record.customs_vat_value



    def _none(self):
        pass

    def _check_sum(self):
        """ Check if each cost line its valuation lines sum to the correct amount
        and if the overall total amount is correct also """
        prec_digits = 0
        for landed_cost in self:
            total_amount = sum(landed_cost.valuation_adjustment_lines.mapped('additional_landed_cost'))
            if not tools.float_is_zero(total_amount - landed_cost.amount_total, precision_digits=prec_digits):
                return False

            val_to_cost_lines = defaultdict(lambda: 0.0)
            for val_line in landed_cost.valuation_adjustment_lines:
                val_to_cost_lines[val_line.cost_line_id] += val_line.additional_landed_cost
            if any(not tools.float_is_zero(cost_line.price_unit - val_amount, precision_digits=prec_digits)
                   for cost_line, val_amount in val_to_cost_lines.items()):
                return False
        return True
    
    @api.depends('cost_lines')
    def _compute_create_landed_bill(self):
        for elm in self:
            elm.create_landed_bill = len(elm.cost_lines) > 0 and self.env['ir.config_parameter'].sudo().get_param(
                'import_fees.shipping_bill_visible', False)

    def calc_customs_fees_and_open(self):
        if not self.vendor_bill_ids:
            raise UserError(_("Please select a vendor bill"))
        if not self.picking_ids:
            raise UserError(_("Please select at least one picking"))
        # Check if customs fees have already been calculated
        if self.customs_fees_ids:
            # If fees exist, show a confirmation dialog
            return {
                'type': 'ir.actions.act_window',
                'name': _('Recalculate Customs Fees'),
                'res_model': 'import_fees.recalculate.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_landed_cost_id': self.id}
            }
        else:
            # If no fees exist, calculate them directly
            self._compute_customs_fees_ids(recalculate=True)

    # @api.depends('customs_value', 'customs_vat_value')
    # def _compute_customs_value(self):
    #     for record in self:
    #         for cf in record.customs_fees_ids:
    #             cf._compute_tariffs()
    #         record._compute_customs_duties()
    #         record.customs_vat_value = sum([it.vat_value for it in self.customs_fees_ids])
    #         record.total_customs_value = record.customs_value + record.customs_vat_value


    @api.depends('stevedoring', 'demurrage', 'transport', 'storage', 'bank', 'miscellaneous', 'royalty_fee',
                 'freight', 'clearance', 'transit', 'insurance', 'shipping', 'other', 'royalty_fee_info',
                 'customs_value', 'customs_vat_value', 'amount_local_currency'
                 )
    def _compute_total_landed_cost(self):
        for record in self:
            record.total_landed_cost = round_total(record.stevedoring + record.demurrage + record.transport + record.storage +
                                            record.bank + record.miscellaneous + record.royalty_fee + record.freight +
                                            record.clearance + record.transit + record.insurance + record.shipping +
                                            record.other + record.royalty_fee_info + record.customs_value +
                                            record.customs_vat_value + record.amount_local_currency)



    @api.onchange('picking_ids')
    def _onchange_picking_ids(self):
        for picking in self.picking_ids:
            error = False
            if not picking.origin:
                error = {'warning': {
                    'message': (_('The transfer %s has no purchase order.') % picking.name)},
                    'title': _('Transfers')
                }
            if not error and not self.env['purchase.order'].search(
                    [('name', '=', picking.origin)]).mapped('invoice_ids'):
                error = {
                    'warning': {'message': (_('The transfer %s\'s purchase order (%s) has no vendor bill.') % (
                        picking.name, picking.origin))},
                    'title': _('Transfers')
                }
            if error:
                self.picking_ids -= picking
                return error

    @api.onchange('picking_ids', 'vendor_bill_ids')
    @api.depends('picking_ids', 'vendor_bill_ids')
    def _compute_received_products_ids(self):
        for record in self:
            if self.picking_ids and self.vendor_bill_ids:
                stock_move_line_ids = self.env['stock.move.line'].search(
                    [('picking_id', 'in', self.picking_ids.ids)])
                act_move_line_ids = self.env['account.move.line'].search([('move_id', 'in', self.vendor_bill_ids.ids)])
                records = []
                for act_move_line_id in act_move_line_ids:
                    stock_item = False
                    for elm in stock_move_line_ids:
                        if elm.product_id == act_move_line_id.product_id:
                            stock_item = elm
                            stock_move_line_ids -= elm
                            break
                    if stock_item:
                        records.append((0, 0, {
                            'move_id': stock_item.move_id.id,
                            'product_id': stock_item.product_id.id,
                            'currency_id': act_move_line_id.currency_id.id,
                            'quantity': stock_item.quantity,
                            'price_unit': act_move_line_id.price_unit,
                            'local_currency_id': self.company_id.currency_id.id,
                            'price_total': stock_item.quantity * act_move_line_id.price_unit,
                            'local_price_total': act_move_line_id.currency_id._convert(from_amount=
                                stock_item.quantity * act_move_line_id.price_unit, to_currency= self.currency_id, round=False),
                        }))
                landed_costs_lines = act_move_line_ids.filtered(
                    lambda it: it.is_landed_costs_line and it.product_id.id != self.env.ref('import_fees.customs').id)
                for item in landed_costs_lines:
                    attr = False
                    try:
                        attr = item.product_id.get_external_id()[item.product_id.id].split('.')[
                            1] if item.product_id.get_external_id() else item.product_id.code
                        # if attr is str
                        if isinstance(attr, str):
                            record.__setattr__(attr, item.price_subtotal)
                        record.update_landed_cost_line(item.product_id.code, item.price_subtotal,
                                                       'by_current_cost_price',
                                                       move_line=item)
                    except Exception as e:
                        # we update landed costs on best effort, so just log the error
                        logger = logging.getLogger(__name__)
                        logger.error('Error updating landed cost line for : ', attr)
                        pass
                self.received_products_ids = [(5,)]
                self.received_products_ids = records
            else:
                self.received_products_ids = [(5,)]

    def _compute_create(self):
        pass

    def _compute_customs_fees_ids(self, recalculate=False):
        if self.received_products_ids:
            # create a list of all hs codes in the received products
            hs_codes = set([it.hs_code_id for it in self.received_products_ids])
            for harmonized_code_id in hs_codes:
                existing = self.customs_fees_ids.search(
                    [('landed_costs_id', '=', self.id), ('harmonized_code_id', '=', harmonized_code_id.id)])
                myfields = ['cif_value', 'com_value', 'exm_value', 'vat_value', 'cid_value', 'surcharge_value',
                            'pal_value', 'eic_value', 'cess_levy_value', 'excise_duty_value', 'srl_value', 'ridl_value',
                            'sscl_value']
                OldValue = mynamedtuple('OldValue', myfields, defaults=(0.0,) * len(myfields))
                data = self.calculate_tariffs(harmonized_code_id,
                                              old_value=OldValue(
                                                  cif_value=existing and existing[0].cif_value or 0.0,
                                                  com_value=existing and existing[0].com_value or 0.0,
                                                  exm_value=existing and existing[0].exm_value or 0.0,
                                                  vat_value=existing and existing[0].vat_value or 0.0,
                                                  cid_value=existing and existing[0].cid_value or 0.0,
                                                  surcharge_value=existing and existing[0].surcharge_value or 0.0,
                                                  pal_value=existing and existing[0].pal_value or 0.0,
                                                  eic_value=existing and existing[0].eic_value or 0.0,
                                                  cess_levy_value=existing and existing[0].cess_levy_value or 0.0,
                                                  excise_duty_value=existing and existing[0].excise_duty_value or 0.0,
                                                  srl_value=existing and existing[0].srl_value or 0.0,
                                                  ridl_value=existing and existing[0].ridl_value or 0.0,
                                                  sscl_value=existing and existing[0].sscl_value or 0.0,
                                              ),
                                              recalculate=recalculate
                                              )
                if existing:
                    existing.update(data)
                else:
                    data['landed_costs_id'] = self.id
                data['harmonized_code_id'] = harmonized_code_id.id
                self.customs_fees_ids.create(data)
                self.customs_vat_value = sum([it.vat_value for it in self.customs_fees_ids])

    def calculate_tariffs(self, hs, old_value=False, recalculate=False):
        use_old_value = old_value if (old_value and not recalculate) else False
        exchange_rate = self.currency_id.with_context(date=self.date).rate
        currency_rate = self.company_id.currency_id.with_context(date=self.date).rate
        declared_value_local = sum([it.local_price_total for it in self.received_products_ids if
                                    it.hs_code_id.id == hs.id]) * exchange_rate
        proportion = declared_value_local / (self.amount_local_currency * (
                exchange_rate / currency_rate)) if self.amount_local_currency else 0.0
        com_value = round_tariff(hs.com_value) if not use_old_value else use_old_value.com_value
        exm_value = round_tariff(hs.exm_value) if not use_old_value else use_old_value.exm_value
        cif_value = round_tariff(
            declared_value_local + proportion * (
                    self.insurance + self.freight)) if not use_old_value else use_old_value.cif_value
        cid_value = round_tariff(cif_value * hs.cid_rate) if not use_old_value else use_old_value.cid_value
        surcharge_value = round_tariff(cid_value * hs.surcharge_rate) if not use_old_value else use_old_value.surcharge_value
        pal_value = round_tariff(cif_value * hs.pal_rate) if not use_old_value else use_old_value.pal_value
        eic_value = round_tariff(cif_value * hs.eic_rate) if not use_old_value else use_old_value.eic_value
        cess_levy_value = round_tariff(
            (cif_value + (cif_value * 0.1)) * hs.cess_levy_rate) if not use_old_value else use_old_value.cess_levy_value
        excise_duty_value = round_tariff(
            cif_value * hs.excise_duty_rate) if not use_old_value else use_old_value.excise_duty_value
        vat_value = round_tariff(((cif_value * 1.1) + (
                cid_value + pal_value + eic_value + cess_levy_value + excise_duty_value)) * hs.vat_rate) if not use_old_value else use_old_value.vat_value
        srl_value = round_tariff((
                                 cid_value + surcharge_value + excise_duty_value) * hs.srl_rate) if not use_old_value else use_old_value.srl_value
        ridl_value = round_tariff((cid_value + cif_value + surcharge_value + pal_value + cess_levy_value +
                           vat_value + excise_duty_value + srl_value) * hs.ridl_rate) if not use_old_value else use_old_value.ridl_value
        sscl_value = round_tariff((cif_value + 0.1 * cif_value + cid_value + pal_value + cess_levy_value +
                           excise_duty_value) * hs.sscl_rate) if not use_old_value else use_old_value.sscl_value
        customs_amount = round_total((cid_value + surcharge_value + pal_value + eic_value + cess_levy_value +
                               excise_duty_value + ridl_value + srl_value + sscl_value + com_value + exm_value))
        return {
            'rate': customs_amount / declared_value_local if declared_value_local else 0.0,
            'value': declared_value_local,
            'com_value': com_value,
            'exm_value': exm_value,
            'amount': customs_amount,
            'cif_value': cif_value,
            'cid_value': cid_value,
            'surcharge_value': surcharge_value,
            'pal_value': pal_value,
            'eic_value': eic_value,
            'cess_levy_value': cess_levy_value,
            'excise_duty_value': excise_duty_value,
            'vat_value': vat_value,
            'srl_value': srl_value,
            'ridl_value': ridl_value,
            'sscl_value': sscl_value,
        }

    @api.depends('vendor_bill_ids', 'picking_ids', 'received_products_ids')
    def _compute_currency_value(self):
        self.amount_foreign_currency = sum(item.price_total for item in self.received_products_ids)

    # Retrieve or create tax rates
    def get_or_create_tax(self, amount):
        tax = self.env['account.tax'].search([('amount', '=', amount), ('type_tax_use', '=', 'purchase')], limit=1)
        if not tax:
            tax = self.env['account.tax'].create({
                'name': f'Tax {amount}%',
                'amount': amount,
                'amount_type': 'percent',
                'type_tax_use': 'purchase',
                'display_name': f'{amount}%',
                # Assuming these are purchase taxes
                # Add other necessary fields according to your tax configuration
            })
        else:
            tax = tax[0]
        return tax

    def button_create_landed_bill(self):
        def safe_flatten(lst, max_depth=10):
            result = []
            stack = [(lst, 0)]
            while stack:
                current, depth = stack.pop()
                if depth > max_depth:
                    result.append(current)
                    continue
                if isinstance(current, (bytes, str)) or not isinstance(current, collections.abc.Iterable):
                    result.append(current)
                else:
                    stack.extend((item, depth + 1) for item in reversed(current))
            return result

        # Search for all shipping bills with the same vendor bill by invoice origin
        lc_bills = self.env['account.move'].search(
            [('invoice_origin', '=', self.name), ('is_landed_bill', '=', True)])
        if lc_bills:
            return {
                'type': 'ir.actions.act_window',
                'name': _("Landed Costs Bill"),
                'res_model': 'account.move',
                'res_id': lc_bills[0]['id'],
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'current',
            }
        else:
            account_inv_line = self.env['account.account'].search([
                ('company_id', '=', self.env.company.id),
                ('account_type', '=', 'asset_current'),
                ('id', '!=', self.env.company.account_journal_early_pay_discount_gain_account_id.id)
            ], limit=1)
            items = []
            customs_id = self.env.ref('import_fees.customs')
            for item in self.cost_lines:
                if item.product_id.id != customs_id.id:
                    items.append((0, 0, {
                        'product_id': item.product_id.id,
                        'quantity': 1,
                        'price_unit': item.price_unit,
                        'account_id': account_inv_line.id,
                        'name': item.name,
                    }))
            vendor_bill_id_invoice_line_ids = safe_flatten(self.vendor_bill_ids.mapped('invoice_line_ids'))
            for item in vendor_bill_id_invoice_line_ids:
                matching_customs_fees_item = next(iter([it for it in self.customs_fees_ids if
                                                        it.harmonized_code_id.id ==
                                                        item.product_id.search_harmonized_code_id().id]),
                                                  False)
                if matching_customs_fees_item:
                    price_subtotal_local_currency = item.price_subtotal
                    proportion = price_subtotal_local_currency / sum(
                        [it.value for it in self.customs_fees_ids if
                         it.harmonized_code_id.id ==
                         item.product_id.search_harmonized_code_id().id])
                    product_id = self.env.ref('import_fees.customs')
                    if matching_customs_fees_item.amount:
                        items.append((0, 0, {
                            'product_id': product_id.id,
                            'quantity': 1,
                            'price_unit': matching_customs_fees_item.amount * proportion,
                            'account_id': account_inv_line.id,
                            'name': "Customs / %s" % (item.product_id.name),
                        }))
                    if matching_customs_fees_item.vat_value:
                        items.append((0, 0, {
                            'product_id': product_id.id,
                            'quantity': 1,
                            'price_unit': matching_customs_fees_item.vat_value * proportion,
                            'account_id': account_inv_line.id,
                            'name': "VAT / %s" % (item.product_id.name),
                        }))
            result = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': self.vendor_bill_ids[0].partner_id.id if self.vendor_bill_ids else False,
                'invoice_line_ids': items,
                'invoice_date': datetime.today().strftime("%Y-%m-%d %H:%M:%S"),
                'invoice_origin': self.name,
                'is_landed_bill': True,
            })
            return {
                'type': 'ir.actions.act_window',
                'name': _("Landed Costs Bill"),
                'res_model': 'account.move',
                'res_id': result['id'],
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'current',
            }

    def compute_landed_cost(self):
        adjustment_lines = self.env['stock.valuation.adjustment.lines']
        adjustment_lines.search([('cost_id', 'in', self.ids)]).unlink()

        towrite_dict = {}
        for cost in self.filtered(lambda cost: cost._get_targeted_move_ids()):
            cost = cost.with_company(cost.company_id)
            rounding = cost.currency_id.rounding
            total_qty = 0.0
            total_cost = 0.0
            total_weight = 0.0
            total_volume = 0.0
            total_line = 0.0
            all_val_line_values = cost.get_valuation_lines()
            all_customs_costs = []
            for val_line_values in all_val_line_values:
                for cost_line in cost.cost_lines:
                    val_line_values.update({'cost_id': cost.id, 'cost_line_id': cost_line.id})
                    self.env['stock.valuation.adjustment.lines'].create(val_line_values)
                hs_code = self.env['product.product'].search([('id', '=', val_line_values.get('product_id'))],
                                                             limit=1).search_harmonized_code_id() or False
                if hs_code:
                    customs_cost = val_line_values.copy()
                    customs_cost.update({
                        'hs_code': hs_code.id,

                    })
                    all_customs_costs.append(customs_cost)
                total_qty += val_line_values.get('quantity', 0.0)
                total_weight += val_line_values.get('weight', 0.0)
                total_volume += val_line_values.get('volume', 0.0)

                former_cost = val_line_values.get('former_cost', 0.0)
                total_cost += former_cost

                total_line += 1

            for line in cost.cost_lines:
                value_split = 0.0
                for valuation in cost.valuation_adjustment_lines:
                    if valuation.cost_line_id and valuation.cost_line_id.id == line.id:
                        if line.split_method == 'by_quantity' and total_qty:
                            per_unit = (line.price_unit / total_qty)
                            value = valuation.quantity * per_unit
                        elif line.split_method == 'by_weight' and total_weight:
                            per_unit = (line.price_unit / total_weight)
                            value = valuation.weight * per_unit
                        elif line.split_method == 'by_volume' and total_volume:
                            per_unit = (line.price_unit / total_volume)
                            value = valuation.volume * per_unit
                        elif line.split_method == 'equal':
                            value = (line.price_unit / total_line)
                        elif line.split_method == 'by_current_cost_price' and total_cost:
                            per_unit = (line.price_unit / total_cost)
                            value = valuation.former_cost * per_unit
                        elif line.split_method == 'by_hscode' and total_qty:
                            move_id = valuation.move_id
                            received_product = self.received_products_ids.filtered(lambda it: it.move_id.id == move_id.id)
                            if received_product:
                                item_price_local = received_product.local_price_total
                                total_price_local = sum([it.local_price_total for it in self.received_products_ids \
                                    if it.product_id.harmonized_code_id.id == received_product.product_id.harmonized_code_id.id])
                                customs_for_hscode = sum([it.amount for it in self.customs_fees_ids \
                                    if it.harmonized_code_id.id == received_product.hs_code_id.id])
                                value = (customs_for_hscode * (item_price_local / total_price_local)) \
                                    if total_price_local else 0.0
                        else:
                            value = (line.price_unit / total_line)

                        if rounding:
                            # value = tools.float_round(value, precision_rounding=rounding, rounding_method='UP')
                            fnc = min if line.price_unit > 0 else max
                            value = fnc(value, line.price_unit - value_split)
                            value_split += value

                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                        else:
                            towrite_dict[valuation.id] += value
        for key, value in towrite_dict.items():
            adjustment_lines.browse(key).write({'additional_landed_cost': value})
        return True

    @api.onchange('stevedoring')
    def update_stevedoring(self):
        self.update_landed_cost_line('stevedoring', self.stevedoring, 'by_current_cost_price')

    @api.onchange('demurrage')
    def update_demurrage(self):
        self.update_landed_cost_line('demurrage', self.demurrage, 'by_current_cost_price')

    @api.onchange('transport')
    def update_transport(self):
        self.update_landed_cost_line('transport', self.transport, 'by_current_cost_price')

    @api.onchange('storage')
    def update_storage(self):
        self.update_landed_cost_line('storage', self.storage, 'by_current_cost_price')

    @api.onchange('bank')
    def update_bank(self):
        self.update_landed_cost_line('bank', self.bank, 'by_current_cost_price')

    @api.onchange('miscellaneous')
    def update_miscellaneous(self):
        self.update_landed_cost_line('miscellaneous', self.miscellaneous, 'by_current_cost_price')

    @api.onchange('royalty_fee')
    def update_royalty_fee(self):
        self.update_landed_cost_line('royalty_fee', self.royalty_fee, 'by_current_cost_price')

    @api.onchange('freight')
    def update_freight(self):
        self.update_landed_cost_line('freight', self.freight, 'by_current_cost_price')

    @api.onchange('clearance')
    def update_clearance(self):
        self.update_landed_cost_line('clearance', self.clearance, 'by_current_cost_price')

    @api.onchange('transit')
    @api.depends('transit')
    def update_transit(self):
        self.update_landed_cost_line('transit', self.transit, 'by_current_cost_price')

    @api.onchange('insurance')
    def update_assurance(self):
        self.update_landed_cost_line('insurance', self.insurance, 'by_current_cost_price')

    @api.onchange('shipping')
    def update_dhl_fedex_ups(self):
        self.update_landed_cost_line('shipping', self.shipping, 'by_current_cost_price')

    @api.onchange('other')
    def update_others(self):
        self.update_landed_cost_line('other', self.other, 'by_current_cost_price')

    @api.onchange('royalty_fee_info')
    def update_royalty_fee_info(self):
        self.update_landed_cost_line('royalty_fee_info', self.royalty_fee_info, 'by_current_cost_price')

    def update_landed_cost_line(self, name, amount, split_method, move_line=False):
        if name or move_line:
            cost_line = False
            if not move_line:
                for it in self.cost_lines:
                    if it.product_id.get_external_id()[it.product_id.id] == ("import_fees.%s" % name):
                        cost_line = it
                        break
            else:
                cost_line = self.env['stock.landed.cost.lines'].search(
                    [('cost_id', '=', self.id), ('product_id', '=', move_line.product_id.id)], limit=1)

            if amount:
                if cost_line:
                    self.cost_lines = [(1, cost_line.id, {'price_unit': amount,
                                                          })]
                elif name:
                    try:
                        product_by_ref = self.env.ref('import_fees.%s' % name)
                        self.cost_lines = [(0, 0, {
                            'cost_id': self.id,
                            'price_unit': amount,
                            'product_id': product_by_ref.id,
                            'split_method': split_method,
                        })]
                    except Exception as e:
                        # Product not found
                        logger = logging.getLogger(__name__)
                        logger.error('Product not found: ', str(name))
                        pass
            else:
                if cost_line:
                    self.cost_lines = [(2, cost_line.id)]



class StockLandedCostLine(models.Model):
    _inherit = 'stock.landed.cost.lines'
    split_method = fields.Selection(selection_add=[('by_hscode', 'By HS Code'), ],
                                    ondelete={'by_hscode': "cascade"},
                                    string='Split Method',
                                    required=True,
                                    help="Equal : Cost will be equally divided.\n"
                                         "By Quantity : Cost will be divided according to product's quantity.\n"
                                         "By Current cost : Cost will be divided according to product's current cost.\n"
                                         "By Weight : Cost will be divided depending on its weight.\n"
                                         "By Volume : Cost will be divided depending on its volume.\n"
                                         "By HS Code : Cost will be divided depending on its Harmonized System Code.")

class RecalculateWizard(models.TransientModel):
    _name = 'import_fees.recalculate.wizard'
    _description = 'Recalculate Customs Fees Wizard'

    landed_cost_id = fields.Many2one('stock.landed.cost', string='Landed Cost', required=True)

    def action_recalculate(self):
        self.ensure_one()
        self.landed_cost_id._compute_customs_fees_ids(recalculate=True)

    def action_cancel(self):
        return True