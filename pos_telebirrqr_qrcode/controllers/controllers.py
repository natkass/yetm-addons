# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
import logging
import json
import pprint
import requests
import time
import random
import string
import hashlib
import base64
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import pss
from base64 import b64encode, b64decode

_logger = logging.getLogger(__name__)


class PostelebirrqrQrcode(http.Controller):
    
    @http.route('/payment/telebirrqr', type='http', methods=['POST'], auth='public', csrf=False)
    def telebirrqr_callback(self):
        """Handle the QR callback from Telebirr and log the request data."""
        
        # Get raw body and headers
        raw_data = request.httprequest.data.decode('utf-8', errors='ignore')
        content_type = request.httprequest.headers.get('Content-Type', '')
        headers = dict(request.httprequest.headers)

        _logger.info("Raw Telebirr QR callback data: %s", raw_data)
        _logger.info("Request Content-Type: %s", content_type)
        _logger.info("Request Headers: %s", pprint.pformat(headers))

        try:
            data = json.loads(raw_data)
            payment_status = http.request.env['telebirrqr.payment'].sudo().search([('trace_no', '=', data['merch_order_id'])], limit=1)

            if not payment_status:
                _logger.warning("No payment status found for merch_order_id: %s", data['merch_order_id'])
                return 'ERROR: Unknown payment'

            order = http.request.env['pos.order'].sudo().search([('pos_reference', '=', payment_status.orignal_ref)], limit=1)

            payment_status.write({
                'status': data.get('trade_status'),
                'txref': data.get('transId')
            })

            if data.get('trade_status') == 'Completed':
                if order:
                    order.write({'checked': True})

            if not data:
                _logger.warning("No data received in Telebirr QR callback")
                return 'ERROR: No data received'

        except json.JSONDecodeError as e:
            _logger.exception("JSON decoding failed: %s", str(e))
            return 'ERROR: Invalid JSON'
        except Exception as e:
            _logger.exception("Unexpected error processing QR callback: %s", str(e))
            return 'ERROR: Internal server error'


        return 'API ENDPOINT REACHED'
    
    def create_timestamp(self):
        return str(int(time.time()))

    def create_nonce_str(self, length=16):
        letters_and_digits = string.ascii_letters + string.digits
        return ''.join(random.choice(letters_and_digits) for _ in range(length))
        
    def sign_request_object(self, request, privateKey):
        """Sign the request with RSA."""
        _logger.info("Signing request with RSA")
        exclude_fields = ["sign", "sign_type", "header", "refund_info", "openType", "raw_request"]
        join = []
        for key in request:
            if key in exclude_fields:
                continue
            if key == "biz_content":
                for k, v in request["biz_content"].items():
                    join.append(f"{k}={str(v)}")
            else:
                join.append(f"{key}={str(request[key])}")
        join.sort()
        input_string = '&'.join(join)
        _logger.info("Input string for signing: %s", input_string)
        signature = self.SignWithRSA(input_string, privateKey)
        _logger.info("Generated signature: %s", signature)
        return signature
    
    def SignWithRSA(self, data, key, sign_type="SHA256withRSA"):
        """Perform RSA signing."""
        _logger.info("Performing RSA signing with sign_type: %s", sign_type)
        _logger.info("Data to sign: %s", data)
        _logger.info("Private key: %s", key)
        if sign_type == "SHA256withRSA":
            _logger.info("Decoding private key for RSA signing")
            key_bytes = b64decode(key.encode("utf-8"))
            rsa_key = RSA.importKey(key_bytes)
            _logger.info("Creating SHA256 digest for data: %s", data)
            digest = SHA256.new(data.encode("utf-8"))
            signer = pss.new(rsa_key)
            _logger.info("Signing digest with RSA")
            signature = signer.sign(digest)
            encoded_signature = b64encode(signature).decode("utf-8")
            _logger.info("Encoded RSA signature: %s", encoded_signature)
            return encoded_signature
        else:
            _logger.error("Unsupported sign_type: %s", sign_type)
            raise ValueError("Only SHA256withRSA is supported")
    
    def apply_fabric_token(self, base_url, fabric_app_id, app_secret):
        url = f"{base_url}/payment/v1/token"
        headers = {
            "Content-Type": "application/json",
            "X-APP-Key": fabric_app_id,
        }
        payload = {
            "appSecret": app_secret
        }

        response = requests.post(url, json=payload, headers=headers, verify=False)
        response.raise_for_status()
        return response.json()

    def query_order(self, base_url, fabric_app_id, merchant_app_id, merchant_code, fabric_token, merch_order_id, private_key):
        req = {
            "timestamp": self.create_timestamp(),
            "nonce_str": self.create_nonce_str(),
            "method": "payment.queryorder",
            "version": "1.0",
        }
        biz = {
            "appid": merchant_app_id,
            "merch_code": merchant_code,
            "merch_order_id": merch_order_id,
        }
        req["biz_content"] = biz
        req["sign"] = self.sign_request_object(req, private_key)
        req["sign_type"] = "SHA256WithRSA"
        
        _logger.info("URL: %s", base_url)

        url = f"{base_url}/payment/v1/merchant/queryOrder"
        headers = {
            "Content-Type": "application/json",
            "X-APP-Key": fabric_app_id,
            "Authorization": fabric_token,
        }
        response = requests.post(url, json=req, headers=headers, verify=False)
        _logger.info("Query order request: %s", json.dumps(req, indent=2))
        _logger.info("Query order response: %s", response.json())
        response.raise_for_status()
        return response.json()

    @http.route('/query_status', type='json', auth='public', methods=['POST'], csrf=False)
    def handle_query_order(self, **post):
        # Required parameters from payload
        base_url = post.get('base_url')
        fabric_app_id = post.get('fabric_app_id')
        app_secret = post.get('app_secret')
        merchant_app_id = post.get('merchant_app_id')
        merchant_code = post.get('merchant_code')
        merch_order_id = post.get('merch_order_id')
        private_key = post.get('private_key')
        _logger.info("Received query order request with parameters: %s", post)

        missing_params = []
        for param in ['base_url', 'fabric_app_id', 'app_secret', 'merchant_app_id', 'merchant_code', 'merch_order_id']:
            if not post.get(param):
                missing_params.append(param)

        if missing_params:
            _logger.error("Missing parameters in request: %s", missing_params)
            return {"success": False, "message": f"Missing parameters: {', '.join(missing_params)}"}

        try:
            token_result = self.apply_fabric_token(base_url, fabric_app_id, app_secret)
            fabric_token = token_result.get("token")
            if not fabric_token:
                _logger.error("Failed to get fabric token: %s", token_result)
                return {"success": False, "message": "Failed to get fabric token"}
            
            _logger.info("Fabric token: %s", fabric_token)

            query_result = self.query_order(base_url, fabric_app_id, merchant_app_id, merchant_code, fabric_token, merch_order_id, private_key)
            _logger.info("Query order result: %s", query_result)
            if query_result["result"] and query_result["result"] == "SUCCESS":
                if query_result["biz_content"]["order_status"] == "PAY_SUCCESS":
                    payment_status = http.request.env['telebirrqr.payment'].sudo().search([('trace_no', '=', merch_order_id)], limit=1)
                    payment_status.write({
                        'status': "Completed",
                        'txref': query_result["biz_content"]["trans_id"]
                    })

            return query_result

        except requests.RequestException as e:
            _logger.error("Request error: %s", e)
            return {"success": False, "message": "Request failed"}

        except Exception as e:
            _logger.error("Internal server error: %s", e)
            return {"success": False, "message": "Internal server error"}