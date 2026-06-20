# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_reconciled = fields.Selection([('unreconciled', 'Unreconciled'), ('reconciled', 'Reconciled')],
                                     string="Is Reconciled ?", default="unreconciled", copy=False)

    flex_bank_reconcile = fields.Boolean(string='Flex Bank Reconcile', related="account_id.flex_bank_reconcile")
    flex_compute = fields.Boolean(string='Match ?', default=False)
    flex_bank_reconcile_id = fields.Many2one('flex.bank.reconcile', compute="compute_flex_bank_reconcile_id")
    flex_bank_reconcile_state = fields.Selection(related='flex_bank_reconcile_id.state')

    def compute_flex_bank_reconcile_id(self):
        for rec in self:
            rec.flex_bank_reconcile_id = False
            if 'flex_bank_reconcile_id' in rec._context.keys():
            # if rec._context['flex_bank_reconcile_id']:
                reconcile_id = int(rec._context['flex_bank_reconcile_id'])
                rec.flex_bank_reconcile_id = self.env['flex.bank.reconcile'].browse(reconcile_id)


class AccountMoveLineCopy(models.Model):
    _name = 'account.move.line.copy'
    _description = 'Copy of Account Move Line'

    reconcile_id = fields.Many2one('flex.bank.reconcile', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True)
    company_currency_id = fields.Many2one('res.currency', readonly=True)
    date = fields.Date('Date', readonly=True)
    move_name = fields.Char(string='Number', readonly=True)
    name = fields.Char(string='Label', readonly=True)
    amount_currency = fields.Monetary(string='Amount in currency', currency_field='currency_id', readonly=True)
    debit = fields.Monetary(string='Debit', currency_field='company_currency_id', readonly=True)
    credit = fields.Monetary(string='Credit', currency_field='company_currency_id', readonly=True)
    balance = fields.Monetary(string='Balance', currency_field='company_currency_id', readonly=True)
    flex_compute = fields.Boolean(string='Match ?', readonly=True)
    is_reconciled = fields.Selection([('unreconciled', 'Unreconciled'), ('reconciled', 'Reconciled')],
                                     string="Is Reconciled ?", default="unreconciled", copy=False, readonly=True)
    account_id = fields.Many2one('account.account', readonly=True)
    partner_id = fields.Many2one('res.partner', readonly=True)
