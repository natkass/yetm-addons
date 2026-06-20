# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    flex_bank_reconcile_difference_journal_id = fields.Many2one(
        'account.journal',
        string='Bank Reconcile Difference Journal',
        help="Accounting journal used to post Reconciliation Difference journal entries.")

    # Accounts

    flex_bank_rec_diff_exp_account_id = fields.Many2one('account.account',
                                                        string="EXP Account",
                                                        help="Account used to write the journal item for EXP Difference Reconciliation.")

    flex_bank_rec_diff_rev_account_id = fields.Many2one('account.account',
                                                        string="REV Account",
                                                        help="Account used to write the journal item for REV Difference Reconciliation.")


