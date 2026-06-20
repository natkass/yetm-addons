import logging
import json
from lxml import etree
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class FlexBankReconcile(models.Model):
    _name = 'flex.bank.reconcile'
    _description = 'Flex Bank Reconciliation'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_default_reconcile_journal(self):
        journal = self.env.company.flex_bank_reconcile_difference_journal_id
        return journal.id if journal else False

    def _get_default_exp_account(self):
        account = self.env.company.flex_bank_rec_diff_exp_account_id
        return account.id if account else False

    def _get_default_rev_account(self):
        account = self.env.company.flex_bank_rec_diff_rev_account_id
        return account.id if account else False

    name = fields.Char(string='Ref', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', compute="compute_currency_id")
    beginning_balance = fields.Monetary('Beginning Balance', digits=3, compute="compute_beginning_balance",
                                        store=True)
    ending_balance = fields.Monetary('Ending Balance', digits='Product Price', required=True, default=0.0)
    ending_date = fields.Date('Ending Date', required=True, default=fields.Date.today())
    difference_balance = fields.Float('Difference', digits=(16, 4), compute="compute_difference_balance", store=False)
    difference_balance_duplicated = fields.Float('Difference', digits=(16, 4), readonly=True)
    account_id = fields.Many2one('account.account', required=True, string='Account',
                                 domain="[('flex_bank_reconcile', '=', True)]")
    account_move_line_ids = fields.Many2many('account.move.line', compute='compute_account_move_lines', store=True)
    account_move_line_copy_ids = fields.One2many('account.move.line.copy', 'reconcile_id', readonly=True)
    filtered_match_line_ids = fields.Many2many('account.move.line.copy', compute='_compute_filtered_match_lines',
                                               string="Filtered Match Lines")
    filtered_unmatch_line_ids = fields.Many2many('account.move.line.copy', compute='_compute_filtered_unmatch_lines',
                                                 string="Filtered UnMatch Lines")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Reconciled')
    ], default='draft', string='Status', readonly=True)

    reconcile_date = fields.Date('Reconciled On', readonly=True, copy=False)
    reconcile_user_id = fields.Many2one('res.users', string='Reconciled By', readonly=True, copy=False)

    reconcile_journal_id = fields.Many2one('account.journal', string='Bank Reconcile Difference Journal',
                                           default=_get_default_reconcile_journal)
    reconcile_exp_account_id = fields.Many2one('account.account', string="EXP Account",
                                               default=_get_default_exp_account)
    reconcile_rev_account_id = fields.Many2one('account.account', string="REV Account",
                                               default=_get_default_rev_account)
    # reports
    sum_bank_credits = fields.Monetary('Sum Credits', compute="compute_sum_credits_debits")
    sum_bank_debits = fields.Monetary('Sum Debits', compute="compute_sum_credits_debits")
    service_charges = fields.Monetary('Service Charges', default=0.0)
    len_bank_credits = fields.Integer('Len Credits', compute="compute_sum_credits_debits")
    len_bank_debits = fields.Integer('Len Debits', compute="compute_sum_credits_debits")

    # report unmatched statements
    sum_bank_credits_unmatched = fields.Monetary('Sum Credits', compute="compute_sum_credits_debits")
    sum_bank_debits_unmatched = fields.Monetary('Sum Debits', compute="compute_sum_credits_debits")
    service_charges_unmatched = fields.Monetary('Service Charges', default=0.0)
    len_bank_credits_unmatched = fields.Integer('Len Credits', compute="compute_sum_credits_debits")
    len_bank_debits_unmatched = fields.Integer('Len Debits', compute="compute_sum_credits_debits")

    # Reconcile on
    reconcile_method = fields.Selection(string='Reconcile Compute On', related="account_id.reconcile_method",
                                        default='amount_in_currency')

    def set_to_draft(self):
        """
        Set the state to draft for reconciliation records and perform related actions.
        """
        # Step 1: Check for the last reconciled record
        last_account_reconcile_id = self.search([('account_id', '=', self.account_id.id), ('state', '=', 'done')],
                                                order="name DESC", limit=1)

        if last_account_reconcile_id and last_account_reconcile_id.id != self.id:
            raise UserError(
                _('You must set to draft from the newer to the older by account. Please set the newer reconciled records to "Draft" first.'))

        # Step 2: Mark account move lines as unreconciled
        self.account_move_line_ids.filtered(lambda line: line.flex_compute).write({'is_reconciled': 'unreconciled'})

        # Step 3: Delete copied account move lines
        self.account_move_line_copy_ids.sudo().unlink()

        # # Step 4: Reset the record name to 'New'
        # self.name = _('New')

        # Step 5: Set the state to draft
        self.write({'state': 'draft'})

    @api.depends('account_move_line_copy_ids')
    def _compute_filtered_match_lines(self):
        for record in self:
            record.filtered_match_line_ids = record.account_move_line_copy_ids.filtered(lambda r: r.flex_compute)

    @api.depends('account_move_line_copy_ids')
    def _compute_filtered_unmatch_lines(self):
        for record in self:
            record.filtered_unmatch_line_ids = record.account_move_line_copy_ids.filtered(lambda r: not r.flex_compute)

    @api.depends('account_id')
    def compute_currency_id(self):
        for rec in self:
            rec.currency_id = self.env.company.currency_id.id
            if rec.account_id and rec.account_id.currency_id and rec.reconcile_method == 'amount_in_currency':
                rec.currency_id = rec.account_id.currency_id.id

    @api.constrains('ending_date')
    def _check_date(self):
        for record in self:
            if record.ending_date and record.ending_date > fields.Date.today():
                raise ValidationError(_('The selected ending date cannot be after today.'))

    def action_check_all(self):
        for rec in self:
            if rec.state == 'draft':
                rec.account_move_line_ids.write({'flex_compute': True})

    def action_uncheck_all(self):
        for rec in self:
            if rec.state == 'draft':
                rec.account_move_line_ids.write({'flex_compute': False})

    def compute_sum_credits_debits(self):
        for rec in self:
            # For Matched Statements
            credits = [line.amount_currency for line in rec.account_move_line_copy_ids if
                       line.flex_compute and line.debit]
            debits = [line.amount_currency for line in rec.account_move_line_copy_ids if
                      line.flex_compute and line.credit]
            if rec.reconcile_method == 'balance':
                credits = [line.balance for line in rec.account_move_line_copy_ids if line.flex_compute and line.debit]
                debits = [line.balance for line in rec.account_move_line_copy_ids if line.flex_compute and line.credit]

            # Sum
            rec.sum_bank_credits = sum(credits)
            rec.sum_bank_debits = sum(debits)

            # Len
            rec.len_bank_credits = len(credits)
            rec.len_bank_debits = len(debits)

            # For UnMatched Statements
            credits = [line.amount_currency for line in rec.account_move_line_copy_ids if
                       not line.flex_compute and line.debit]
            debits = [line.amount_currency for line in rec.account_move_line_copy_ids if
                      not line.flex_compute and line.credit]
            if rec.reconcile_method == 'balance':
                credits = [line.balance for line in rec.account_move_line_copy_ids if
                           not line.flex_compute and line.debit]
                debits = [line.balance for line in rec.account_move_line_copy_ids if
                          not line.flex_compute and line.credit]

            # Sum
            rec.sum_bank_credits_unmatched = sum(credits)
            rec.sum_bank_debits_unmatched = sum(debits)

            # Len
            rec.len_bank_credits_unmatched = len(credits)
            rec.len_bank_debits_unmatched = len(debits)

    @api.model
    def create(self, vals):
        # Check for existing records with same account_id and state='Draft'
        existing_records = self.search([
            ('account_id', '=', vals.get('account_id')),
            ('state', '=', 'draft')
        ])

        if existing_records:
            raise ValidationError(_('A record with the same account already exists in the Draft state.'))

        return super(FlexBankReconcile, self).create(vals)

    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(_('You cannot delete a record that is in "Reconciled" state.'))
        return super(FlexBankReconcile, self).unlink()

    def action_reconcile_lines(self):
        # Create a journal entry for the difference
        if self.difference_balance != 0:
            raise ValidationError(_('The difference balance must be zero.'))

        # Implement your reconciliation logic here
        for line in self.account_move_line_ids:
            if line.flex_compute:
                line.reconcile()
                line.is_reconciled = 'reconciled'
            self.create_line_copy(line)

        # Save reconcile Date and User
        self.reconcile_date = fields.Date.today()
        self.reconcile_user_id = self.env.user.id

        # Give a sequence number after reconcile
        if self.name == _('New'):
            self.name = self.env['ir.sequence'].next_by_code('flex.bank.reconcile') or _('New')

        # change the status from draft to reconcile
        self.state = 'done'

    def create_line_copy(self, line):
        self.env['account.move.line.copy'].create({
            'reconcile_id': self.id,
            'company_id': line.company_id.id,
            'currency_id': line.currency_id.id,
            'date': line.date,
            'move_name': line.move_id.name,
            'name': line.name,
            'amount_currency': line.amount_currency,
            'debit': line.debit,
            'credit': line.credit,
            'balance': line.balance,
            'flex_compute': line.flex_compute,
            'is_reconciled': line.is_reconciled,
            'account_id': line.account_id.id,
            'partner_id': line.partner_id.id,
            'company_currency_id': line.company_currency_id.id,
        })

    @api.depends('account_id', 'ending_date')
    def compute_account_move_lines(self):
        for rec in self:
            # Delete all records
            rec.account_move_line_ids = False

            # Fill Records
            if rec.account_id and rec.ending_date:
                account_move_line_ids = rec.env['account.move.line'].sudo().search(
                    [('account_id', '=', rec.account_id.id), ('is_reconciled', '=', 'unreconciled'),
                     ('move_id.state', '=', 'posted'),
                     ('date', '<=', rec.ending_date)])

                # Fill all not reconciled records of this account
                rec.account_move_line_ids = [(6, 0, account_move_line_ids.ids)]

    @api.depends('account_id', 'ending_date')
    def compute_beginning_balance(self):
        # initial_value
        for rec in self:
            rec.beginning_balance = 0.0
            if rec.account_id and rec.ending_date:
                account_move_line_ids = rec.env['account.move.line'].sudo().search(
                    [('account_id', '=', rec.account_id.id), ('is_reconciled', '=', 'reconciled'),
                     ('date', '<=', rec.ending_date)])
                rec.beginning_balance = sum(account_move_line_ids.mapped('amount_currency'))
                if rec.reconcile_method == 'balance':
                    rec.beginning_balance = sum(account_move_line_ids.mapped('balance'))

    @api.depends('account_move_line_ids', 'ending_balance', 'state')
    def compute_difference_balance(self):
        # initial_value
        for rec in self:
            rec.difference_balance = rec.ending_balance - rec.beginning_balance
            if rec.account_move_line_ids and rec.state == 'draft':
                # rec.difference_balance = rec.ending_balance - sum(rec.account_move_line_ids.mapped('amount_currency'))
                rec.difference_balance = rec.ending_balance - rec.beginning_balance - sum(
                    [line.amount_currency for line in rec.account_move_line_ids if line.flex_compute])
                if rec.reconcile_method == 'balance':
                    rec.difference_balance = rec.ending_balance - rec.beginning_balance - sum(
                        [line.balance for line in rec.account_move_line_ids if line.flex_compute])

            # when the state Done will compute from the copy lines
            elif rec.account_move_line_copy_ids and rec.state == 'done':
                # rec.difference_balance = rec.ending_balance - sum(rec.account_move_line_copy_ids.mapped('amount_currency'))
                rec.difference_balance = rec.ending_balance - rec.beginning_balance - sum(
                    [line.amount_currency for line in rec.account_move_line_copy_ids if line.flex_compute])
                if rec.reconcile_method == 'balance':
                    rec.difference_balance = rec.ending_balance - rec.beginning_balance - sum(
                        [line.balance for line in rec.account_move_line_copy_ids if line.flex_compute])

            # Duplicate the value
            rec.difference_balance = rec.difference_balance if abs(rec.difference_balance) > 0.001 else 0.0
            rec.difference_balance_duplicated = rec.difference_balance
            print(rec.difference_balance)

            if rec.difference_balance == 0.0:
                pass

    def button_open_difference_reconcile_wizard(self):
        # Get journal_id
        if not self.reconcile_journal_id:
            raise ValidationError(_("There's no Journal for the bank reconciliation difference."))

        # Get exp account
        if not self.reconcile_exp_account_id:
            raise ValidationError(_("There's no EXP Account for the bank reconciliation difference."))

        # Get rev account
        if not self.reconcile_rev_account_id:
            raise ValidationError(_("There's no REV Account for the bank reconciliation difference."))

        context = {
            'default_reconcile_id': self.id,
            'default_account_id': self.account_id.id,
            'default_currency_id': self.currency_id.id,
            'default_reconcile_journal_id': self.reconcile_journal_id.id,
            'default_reconcile_exp_account_id': self.reconcile_exp_account_id.id,
            'default_reconcile_rev_account_id': self.reconcile_rev_account_id.id,
            'default_amount': abs(self.difference_balance),  # set your default values
            'default_date': self.ending_date,  # set your default values
            'default_reconcile_method': self.reconcile_method,
        }
        return {
            'name': 'Reconcile Bank Difference',
            'type': 'ir.actions.act_window',
            'res_model': 'flex.reconcile.bank.difference',
            'view_mode': 'form',
            'view_id': self.env.ref('flex_bank_reconciliation.flex_reconcile_bank_expenses_difference_view_form').id,
            'target': 'new',
            'context': context,
        }
