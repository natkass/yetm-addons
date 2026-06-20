# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountAccount(models.Model):
    _inherit = 'account.account'

    flex_bank_reconcile = fields.Boolean(string='Flex Bank Reconcile')
    reconcile_method = fields.Selection([
        ('amount_in_currency', 'Amount in Currency'),
        ('balance', 'Balance')
    ], string='Reconcile Compute On', required=True, default='amount_in_currency')
