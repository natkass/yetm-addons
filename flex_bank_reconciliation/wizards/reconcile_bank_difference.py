from odoo import api, fields, models, _


class FlexReconcileBankDifferenceWizard(models.TransientModel):
    _name = 'flex.reconcile.bank.difference'
    _description = 'Reconcile Bank Difference Wizard'

    reconcile_id = fields.Many2one('flex.bank.reconcile')
    type = fields.Selection([('exp', 'Expense'), ('rev', 'Revenue')], required=True, string="Type", default="exp")
    account_id = fields.Many2one('account.account', string="Account")
    amount = fields.Float(string='Amount', digits=(16, 10), required=True)
    date = fields.Date(string='Date', required=True)
    currency_id = fields.Many2one('res.currency')
    partner_id = fields.Many2one('res.partner')

    reconcile_journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    reconcile_exp_account_id = fields.Many2one('account.account', string="EXP Account", required=True)
    reconcile_rev_account_id = fields.Many2one('account.account', string="REV Account", required=True)
    reconcile_label = fields.Char('Label', default="Bank reconciliation")
    reconcile_method = fields.Selection([
        ('amount_in_currency', 'Amount in Currency'),
        ('balance', 'Balance')
    ], string='Reconcile Compute On', required=True, default='amount_in_currency')

    def create_difference_journal_entry(self):
        # Create the journal
        move_id = self.env['account.move'].sudo().create({
            'move_type': 'entry',
            'date': self.date,
            'ref': "Bank Reconciliation Difference for account number %s" % (self.account_id.name),
            'journal_id': self.reconcile_journal_id.id,
            'currency_id': self.currency_id.id,
            # 'partner_id': self.partner_id.id,
            'line_ids': [
                (0, 0, {
                    # 'debit': 0.0,
                    # 'credit': self.amount,
                    'amount_currency': - self.amount,
                    'name': self.reconcile_label,
                    'partner_id': self.partner_id.id if self.partner_id else False,
                    'currency_id': self.currency_id.id,
                    'account_id': self.account_id.id if self.type == "exp" else self.reconcile_rev_account_id.id,
                }),
                (0, 0, {
                    'amount_currency': self.amount,
                    # 'debit': self.amount,
                    #     'credit': 0.0,
                    'name': self.reconcile_label,
                    'partner_id': self.partner_id.id if self.partner_id else False,
                    'currency_id': self.currency_id.id,
                    'account_id': self.reconcile_exp_account_id.id if self.type == "exp" else self.account_id.id,
                }),
            ],
        })
        # Action post
        move_id.action_post()

        # Search on new journal entry line that have same account
        move_line_ids = move_id.line_ids.filtered(lambda line: line.account_id.id == self.account_id.id)
        move_line_ids = move_line_ids.filtered(lambda line: line.date <= self.reconcile_id.ending_date)

        # Fill reconcile lines
        self.reconcile_id.account_move_line_ids = [(4, move_line.id) for move_line in move_line_ids]
