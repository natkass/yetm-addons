from odoo import models, api, _
from datetime import datetime
import pytz
from odoo.exceptions import UserError

class PosSession(models.Model):
    """Model inherited to add additional functionality"""
    _inherit = 'pos.session'

    # @api.model
    # def get_server_time(device_timezone):
    #     # Get current UTC time with timezone awareness
    #     utc_now = datetime.now(pytz.utc)
    #     # Convert to device's timezone
    #     device_tz = pytz.timezone(device_timezone)
    #     server_time_device_tz = utc_now.astimezone(device_tz)
    #     return server_time_device_tz.isoformat()

    @api.model
    def get_server_time(self):
        ethiopia_tz = pytz.timezone('Africa/Addis_Ababa')
        utc_now = datetime.now(ethiopia_tz)
        return utc_now.isoformat()
    
    def _pos_ui_models_to_load(self):
        """Used to super the _pos_ui_models_to_load"""
        result = super()._pos_ui_models_to_load()
        result += [
            'void.reason'
        ]
        return result

    def _loader_params_void_reason(self):
        """Used to override the default settings for loading fields"""
        return {
            'search_params': {
                'fields': ['reason'],
            },
        }

    def _get_pos_ui_void_reason(self, params):
        """Used to get the parameters"""
        return self.env['void.reason'].search_read(
            **params['search_params'])

    def _loader_params_product_product(self):
        params = super()._loader_params_product_product()
        # this is usefull to evaluate reward domain in frontend
        params['search_params']['fields'].append('service_charge')
        params['search_params']['fields'].append('product_count')
        params['search_params']['fields'].append('bom_ids')
        return params
    def _loader_params_res_users(self):
        params = super()._loader_params_res_users()
        params["search_params"]["fields"].extend(["pos_login_direct", "pos_logout_direct", "pos_pin", "branch"])
        return params
    def _loader_params_account_tax(self):
        params = super()._loader_params_account_tax()
        params['search_params']['fields'].append('type_tax_use')
        return params
    def _loader_params_res_partner(self):
        vals = super()._loader_params_res_partner()
        vals["search_params"]["fields"] += ["discount_customer"]
        return vals
    
    # def _prepare_line(self, order_line):
        # """ Derive from order_line the order date, income account, amount and taxes information.

        # These information will be used in accumulating the amounts for sales and tax lines.
        # """
        # def get_income_account(order_line):
        #     product = order_line.product_id
        #     income_account = product.with_company(order_line.company_id)._get_product_accounts()['income'] or self.config_id.journal_id.default_account_id
        #     if not income_account:
        #         raise UserError(_('Please define income account for this product: "%s" (id:%d).',
        #                           product.name, product.id))
        #     return order_line.order_id.fiscal_position_id.map_account(income_account)

        # company_domain = self.env['account.tax']._check_company_domain(order_line.order_id.company_id)
        # tax_ids = order_line.tax_ids_after_fiscal_position.filtered_domain(company_domain)
        # sign = -1 if order_line.qty >= 0 else 1

        # price = sign * order_line.price_unit * (1 - (order_line.discount or 0.0) / 100.0)
        # # Apply service charge
        # price_with_service_charge = price * (1 + (order_line.service_charge or 0.0) / 100.0)

        # # _logger.info("+++++++++++++++++ order_line: %s", order_line.read())
        # # _logger.info("+++++++++++++++++ price without service charge: %s", price)
        # # _logger.info("+++++++++++++++++ price with service charge: %s", price_with_service_charge)

        # # The 'is_refund' parameter is used to compute the tax tags. Ultimately, the tags are part
        # # of the key used for summing taxes. Since the POS UI doesn't support the tags, inconsistencies
        # # may arise in 'Round Globally'.
        # check_refund = lambda x: x.qty * x.price_unit < 0
        # is_refund = check_refund(order_line)
        # tax_data = tax_ids.compute_all(price_unit=price_with_service_charge, quantity=abs(order_line.qty), currency=self.currency_id, is_refund=is_refund, fixed_multiplicator=sign)
        # taxes = tax_data['taxes']
        # # For Cash based taxes, use the account from the repartition line immediately as it has been paid already
        # for tax in taxes:
        #     tax_rep = self.env['account.tax.repartition.line'].browse(tax['tax_repartition_line_id'])
        #     tax['account_id'] = tax_rep.account_id.id
        # date_order = order_line.order_id.date_order
        # taxes = [{'date_order': date_order, **tax} for tax in taxes]
        # return {
        #     'date_order': order_line.order_id.date_order,
        #     'income_account_id': get_income_account(order_line).id,
        #     'amount': order_line.price_subtotal,
        #     'taxes': taxes,
        #     'base_tags': tuple(tax_data['base_tags']),
        # }