from odoo import models, fields

import logging

_logger = logging.getLogger(__name__)

class PaymentStatus(models.Model):
    _name = 'cardpay.payment.status'

    price = fields.Float(string='Price')
    trace_number = fields.Char(string='Ref Number')
    otp = fields.Char(string='OTP')
    pos_order_id = fields.Many2one('pos.order', string='POS Order', ondelete='set null')
    card_payment_receipt_data = fields.Char(related='pos_order_id.card_payment_receipt_data', string='Receipt Data', readonly=True)
    signature = fields.Char(related='pos_order_id.signature', string='Signature', readonly=True)
    status = fields.Char(string='Status')
    date = fields.Datetime(string='Date', default=lambda self: fields.Datetime.now())

    def find_pay_confirmed_card(self, trace_number):
        _logger.info(f"Searching for payment status with trace number: {trace_number}")
        payment_status = self.env['cardpay.payment.status'].sudo().search([('trace_number', '=', trace_number)])
        if payment_status:
            _logger.info(f"Payment status found: {payment_status.status}")
            if payment_status.status == "Confirmed":
                _logger.info("Payment confirmed.")
                pos_order = payment_status.pos_order_id
                return {
                    'msg': 'Success',
                    'receiptData': pos_order.card_payment_receipt_data if pos_order else '',
                    'signature': pos_order.signature if pos_order else '',
                }
            elif payment_status.status == "Failed":
                _logger.warning("Payment failed.")
                return {'msg': 'Failed'}
        else:
            _logger.warning(f"No payment status found for trace number: {trace_number}")
            return {'msg': 'Failed'}