# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Journal Accounts Settings

    flex_bank_reconcile_difference_journal_id = fields.Many2one(
        'account.journal',
        string='Bank Reconcile Difference Journal',
        related="company_id.flex_bank_reconcile_difference_journal_id", readonly=False,
        help="Accounting journal used to post Reconciliation Difference journal entries.")

    # Accounts

    flex_bank_rec_diff_exp_account_id = fields.Many2one('account.account',
                                                        string="EXP Account",
                                                        related="company_id.flex_bank_rec_diff_exp_account_id",
                                                        readonly=False,
                                                        help="Account used to write the journal item for EXP Difference Reconciliation.")

    flex_bank_rec_diff_rev_account_id = fields.Many2one('account.account',
                                                        string="REV Account",
                                                        related="company_id.flex_bank_rec_diff_rev_account_id",
                                                        readonly=False,
                                                        help="Account used to write the journal item for REV Difference Reconciliation.")


