from odoo import fields, models, api
import logging
import re
import json

_logger = logging.getLogger(__name__)

class PosOrderInherit(models.Model):
    _inherit = 'pos.order'

    card_payment_receipt_data = fields.Char('Card Payment Receipt Data')
    signature = fields.Char('Signature Image', help="Image of the card payment receipt signature.")
    
    @api.model
    def _order_fields(self, ui_order):
        vals = super(PosOrderInherit, self)._order_fields(ui_order)
        vals.update({
            'card_payment_receipt_data': ui_order.get('card_payment_receipt_data', ''),
            'signature': ui_order.get('signature', ''),
        })

        return vals

    def _export_for_ui(self, order):
        result = super(PosOrderInherit, self)._export_for_ui(order)
        result.update({
            'card_payment_receipt_data': order.card_payment_receipt_data,
            'signature': order.signature,
        })
        return result

    def _extract_trace_number(self):
        # Extracts everything after 'Order' or 'Self Order' (case-insensitive)
        if self.pos_reference:
            match = re.search(r'(?:Self\s+Order|Order)\s*(.+)', self.pos_reference, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return self.pos_reference

    def _update_cardpay_status(self, vals):
        # Helper to update cardpay.payment.status with pos_order_id and status
        trace_number = self._extract_trace_number()
        status_rec = self.env['cardpay.payment.status'].sudo().search([
            ('trace_number', '=', trace_number)
        ], limit=1)
        if status_rec and not status_rec.pos_order_id:
            status_rec.write({'pos_order_id': self.id})
        # If receipt data is set, update status field
        receipt_data = vals.get('card_payment_receipt_data')
        if receipt_data and status_rec:
            try:
                data = json.loads(receipt_data) if isinstance(receipt_data, str) else receipt_data
                status_val = (data.get('status') or data.get('trxnStatus') or '').capitalize()
                if status_val:
                    if status_val.lower() == 'success':
                        status_rec.write({'status': 'Confirmed'})
                    elif status_val.lower() == 'failed':
                        status_rec.write({'status': 'Failed'})
                    else:
                        status_rec.write({'status': status_val})
            except Exception as e:
                _logger.warning(f"Could not parse receipt data for status update: {e}")

    def write(self, vals):
        res = super(PosOrderInherit, self).write(vals)
        # After write, if card_payment_receipt_data or signature is set, update cardpay.payment.status
        for order in self:
            if vals.get('card_payment_receipt_data') or vals.get('signature'):
                order._update_cardpay_status(vals)
        return res

    @api.model
    def create(self, vals):
        order = super(PosOrderInherit, self).create(vals)
        # After create, if card_payment_receipt_data or signature is set, update cardpay.payment.status
        if vals.get('card_payment_receipt_data') or vals.get('signature'):
            order._update_cardpay_status(vals)
        return order