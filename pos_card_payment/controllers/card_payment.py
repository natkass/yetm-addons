from odoo.http import request

from odoo import http, _
import json

import logging

_logger = logging.getLogger(__name__)

class CardPayController(http.Controller):
    @http.route('/cardpayment/verify', auth='public', type='json', methods=['POST'], csrf=False)
    def cardpay_callback(self, **k):
        try:
            jsondata = json.loads(request.httprequest.data)
            _logger.info("Received payment verification callback: %s", jsondata)

            # Extract data from request
            order_ref = jsondata.get('orderRef')
            otp = jsondata.get('otp')
            receipt_data = jsondata.get('receiptData', '')
            sign = jsondata.get('sign', '')
            status = jsondata.get('status')
            _logger.info("Extracted data - orderRef: %s, otp: %s, receiptData: %s, status: %s, signature: %s", order_ref, otp, receipt_data, status, sign)
            # Validate required fields
            if not order_ref:
                _logger.error("Missing orderRef in the request.")
                return {'msg': 'Error', 'error': 'Missing order reference'}

            if not otp:
                _logger.error("Missing OTP in the request.")
                return {'msg': 'Error', 'error': 'Missing OTP'}

            if not status:
                _logger.error("Missing payment status in the request.")
                return {'msg': 'Error', 'error': 'Missing payment status'}

            # Find the payment status entry using both orderRef (trace_number) and OTP
            payment_status = request.env['cardpay.payment.status'].sudo().search([
                ('trace_number', '=', order_ref),
                ('otp', '=', otp)
            ], limit=1)

            if not payment_status:
                _logger.warning("No matching payment entry found for orderRef: %s and provided OTP.", order_ref)
                return {'msg': 'Error', 'error': 'Invalid order reference or OTP'}

            # Update payment status
            if status.lower() == 'success':
                _logger.info("Payment confirmed for orderRef: %s", order_ref)
                payment_status.write({'status': "Confirmed"})
                # Find related pos.order and write receipt/signature there
                pos_order = request.env['pos.order'].sudo().search([('pos_reference', '=', order_ref)], limit=1)
                if pos_order:
                    pos_order.write({'card_payment_receipt_data': receipt_data})
                    if sign and sign.lower() != 'null':
                        pos_order.write({'signature': sign})
            elif status.lower() == 'failed':
                _logger.warning("Payment failed for orderRef: %s", order_ref)
                payment_status.write({'status': "Failed"})
            else:
                _logger.error("Invalid status message received: %s", status)
                return {'msg': 'Error', 'error': 'Invalid payment status'}

            return {'msg': 'Success'}

        except json.JSONDecodeError as e:
            _logger.error("Invalid JSON format received: %s", str(e))
            return {'msg': 'Error', 'error': 'Invalid JSON format'}

        except Exception as e:
            _logger.exception("Unexpected error occurred: %s", str(e))
            return {'msg': 'Error', 'error': 'Internal server error'}
        
    @http.route('/create_payment_card', type='json', auth='public', csrf=False)
    def create_resource_endpoint(self, **kw):
        _logger.info("Received /create_payment request with data: %s", kw)

        try:
            trace_number = kw.get("trace_number")
            price = kw.get("price")
            otp = kw.get("otp")

            if not trace_number or not price or not otp:
                _logger.warning("Missing required parameters. Trace number: %s, Price: %s, OTP: %s", trace_number, price, otp)
                return {'msg': 'Error', 'error': 'Missing trace_number, price, or otp'}

            _logger.info("Looking for existing payment with trace number: %s", trace_number)

            existing_payment = request.env['cardpay.payment.status'].sudo().search([('trace_number', '=', trace_number)], limit=1)

            if existing_payment:
                _logger.info("Payment already exists for trace number: %s | Status: %s | OTP: %s", trace_number, existing_payment.status, existing_payment.otp)
                return {'msg': 'Exists', 'status': existing_payment.status, 'otp': existing_payment.otp}

            _logger.info("Creating new payment record with price: %s, trace_number: %s, otp: %s", price, trace_number, otp)

            payment_status = request.env['cardpay.payment.status'].sudo().create({
                'price': price,
                'trace_number': trace_number,
                'otp': otp,
                # Try to link to pos.order
                'pos_order_id': request.env['pos.order'].sudo().search([('pos_reference', '=', trace_number)], limit=1).id,
            })

            _logger.info("Created new payment status record with ID: %s", payment_status.id)

            return {'msg': 'Created', 'status': payment_status.status, 'otp': payment_status.otp}

        except Exception as e:
            _logger.exception("Exception occurred while processing /create_payment")
            return {'msg': 'Error', 'error': str(e)}

    @http.route('/change_status', type='json', auth='public', csrf=False)
    def change_status(self, **kw):
        _logger.info("Received /change_status request with data: %s", kw)

        try:
            trace_number = kw.get("trace_number")
            status = kw.get("status")

            if not trace_number or not status:
                _logger.warning("Missing required parameters. Trace number: %s, Status: %s", trace_number, status)
                return {'msg': 'Error', 'error': 'Missing trace_number or status'}

            _logger.info("Looking for existing payment with trace number: %s", trace_number)

            existing_payment = request.env['cardpay.payment.status'].sudo().search([('trace_number', '=', trace_number)], limit=1)

            if existing_payment:
                _logger.info("Payment already exists for trace number: %s | Status: %s | OTP: %s", trace_number, existing_payment.status, existing_payment.otp)
                existing_payment.write({'status': status})
                return True
            else:
                return False

        except Exception as e:
            _logger.exception("Exception occurred while processing /change_status")
            return {'msg': 'Error', 'error': str(e)}