from odoo import fields, models, _
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class telebirrqrPayment(models.Model):
    _name = 'telebirrqr.payment'
    
    date = fields.Datetime(string='Date', default=lambda self: fields.Datetime.now())
    orignal_ref = fields.Char('POS Reference')
    trace_no = fields.Char('Trace Number')
    txref = fields.Char('TX Reference')
    price = fields.Float(string='Price')
    status = fields.Char('Payment Confirm')
    session_id = fields.Many2one('pos.session', string='POS Session')
    
    def find_pay_confirmed_telebirr(self, orignal_ref):
        _logger.info("Checking payment status for original_ref: %s", orignal_ref)

        try:
            payment_status = request.env['telebirrqr.payment'].sudo().search([('orignal_ref', '=', orignal_ref)], limit=1)

            if payment_status:
                _logger.info("Payment record found: ID=%s, status=%s", payment_status.id, payment_status.status)

                if payment_status.status == "Completed":
                    _logger.info("Payment confirmed for original_ref: %s", orignal_ref)
                    return {'msg': 'Success'}

                elif payment_status.status == "Failed":
                    _logger.warning("Payment failed for original_ref: %s", orignal_ref)
                    return {'msg': 'Failed'}

                else:
                    _logger.info("Payment status is %s for original_ref: %s", payment_status.status, orignal_ref)
                    return {'msg': 'Pending'}

            else:
                _logger.warning("No payment record found for original_ref: %s", orignal_ref)
                return {'msg': 'Failed'}

        except Exception as e:
            _logger.exception("Error checking payment confirmation for original_ref: %s", orignal_ref)
            return {'msg': 'Failed', 'error': str(e)}