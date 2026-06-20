from odoo import models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def action_view_account_moves_batch(self):
        all_orders = self.env['pos.order'].search([('session_id', 'in', self.ids)])
        invoice_moves = all_orders.mapped('account_move')
        order_names = all_orders.mapped('name')
        session_names = self.mapped('name')
        session_ids = self.ids

        # # ✅ FIX: Get journals used in payments
        # payment_journals = all_orders.mapped('payment_ids.payment_method_id.journal_id')


        # # Get entries related to payments (bank/cash side)
        # payment_moves = self.env['account.move'].search([
        #     ('journal_id', 'in', payment_journals.ids),
        #     '|',
        #     ('ref', 'in', order_names),
        #     ('ref', 'in', session_names),
        # ])

        # 3. Payment + Reconciliation moves via pos_order_ids
        payment_related_moves = self.env['account.move'].search([
            ('payment_ids.pos_session_id', 'in', session_ids)
        ])

        payment_related_moves_new = self.env['account.move'].search([
            ('pos_payment_ids.session_id', 'in', session_ids)
        ])
        
        stock_moves = self.env['account.move'].search([
            ('stock_move_id.picking_id.pos_session_id', 'in', session_ids)
        ])
        # Get other matching entries (reconciliation, etc.)
        additional_moves = self.env['account.move'].search([
            '|',
            ('ref', 'in', order_names),
            ('ref', 'in', session_names),
            
        ])

        all_moves = (invoice_moves | additional_moves | payment_related_moves | payment_related_moves_new | stock_moves).ids

        return {
            'name': 'Journal Entries',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', all_moves)],
            'context': {'create': False},
        }
