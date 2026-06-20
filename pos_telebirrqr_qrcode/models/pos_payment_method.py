from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
import json
import random
import string
import time
import re
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import pss
from base64 import b64encode, b64decode
import logging

_logger = logging.getLogger(__name__)

class PosPaymentMethodInherit(models.Model):
    _inherit = 'pos.payment.method'
    
    aggregator_id = fields.Char(string="Aggregator ID")
    screen_qr = fields.Boolean(string="On Screen QR Code")
    base_url = fields.Char(string="Telebirr Base URL")
    web_base_url = fields.Char(string="Telebirr Web Base URL")
    fabricAppId = fields.Char(string="Fabric App ID")
    appSecret = fields.Char(string="App Secret")
    merchantAppId = fields.Char(string="Merchant App ID")
    merchantCode = fields.Char(string="Merchant Code")
    privateKey = fields.Char(string="Private Key")


    def _get_payment_terminal_selection(self):
        _logger.info("Retrieving payment terminal selection options")
        return super()._get_payment_terminal_selection() + [('telebirrqr', 'Telebirr QR Code')]

    use_payment_terminal = fields.Selection(
        selection=lambda self: self._get_payment_terminal_selection(),
        string='Use a Payment Terminal',
        help='Record payments with a terminal on this journal.',
        required=False
    )
    hide_use_payment_terminal = fields.Boolean(
        compute='_compute_hide_use_payment_terminal',
        help='Technical field to hide use_payment_terminal when no payment interfaces are installed.'
    )
    is_cash_count = fields.Boolean(string='Cash')
    active = fields.Boolean(default=True)

    @api.depends('is_cash_count')
    def _compute_hide_use_payment_terminal(self):
        _logger.info("Computing hide_use_payment_terminal for payment methods")
        no_terminals = not bool(self._fields['use_payment_terminal'].selection(self))
        for payment_method in self:
            payment_method.hide_use_payment_terminal = no_terminals or payment_method.is_cash_count
            _logger.info("hide_use_payment_terminal for payment method %s: %s", payment_method.id, payment_method.hide_use_payment_terminal)

    @api.onchange('use_payment_terminal')
    def _onchange_use_payment_terminal(self):
        _logger.info("Triggered _onchange_use_payment_terminal")
        pass

    @api.depends('config_ids')
    def _compute_open_session_ids(self):
        _logger.info("Computing open_session_ids for payment methods")
        for payment_method in self:
            open_sessions = self.env['pos.session'].search([
                ('config_id', 'in', payment_method.config_ids.ids),
                ('state', '!=', 'closed')
            ])
            payment_method.open_session_ids = open_sessions
            _logger.info("Found %d open sessions for payment method %s", len(open_sessions), payment_method.id)

    @api.onchange('is_cash_count')
    def _onchange_is_cash_count(self):
        _logger.info("is_cash_count changed to: %s", self.is_cash_count)
        if not self.is_cash_count:
            _logger.info("Unsetting cash_journal_id as is_cash_count is False")
            self.cash_journal_id = False
        else:
            _logger.info("Unsetting use_payment_terminal as is_cash_count is True")
            self.use_payment_terminal = False

    def _is_write_forbidden(self, fields):
        _logger.info("Checking if write is forbidden for fields: %s", fields)
        result = bool(fields and self.open_session_ids)
        _logger.info("Write forbidden: %s", result)
        return result

    def write(self, vals):
        _logger.info("Writing values to pos.payment.method: %s", vals)
        if self._is_write_forbidden(set(vals.keys())):
            open_session_names = ' '.join(self.open_session_ids.mapped('name'))
            _logger.error("Cannot modify payment method due to open sessions: %s", open_session_names)
            raise UserError(
                'Please close and validate the following open PoS Sessions before modifying this payment method.\n'
                'Open sessions: %s' % open_session_names
            )
        result = super().write(vals)
        _logger.info("Successfully wrote values to pos.payment.method")
        return result

    @api.model
    def register_order(self, data):
        """Register the order with Telebirr and return the prepay ID."""
        _logger.info("Registering Telebirr order with data: %s", data)
        pos_ref = data.get('pos_ref')
        amount = data.get('amount')
        orderNumber = data.get('orderNumber')
        base_url = data.get('base_url')
        web_base_url = data.get('web_base_url')
        fabricAppId = data.get('fabricAppId')
        appSecret = data.get('appSecret')
        merchantAppId = data.get('merchantAppId')
        merchantCode = data.get('merchantCode')
        privateKey = data.get('privateKey')
        sessionId = data.get('sessionId')
        aggregator_id = data.get('aggregator_id')

        telebirr_params = {
            'amount': amount,
            'orderNumber': orderNumber,
            'base_url': base_url,
            'web_base_url': web_base_url,
            'fabricAppId': fabricAppId,
            'appSecret': appSecret,
            'merchantAppId': merchantAppId,
            'merchantCode': merchantCode,
            'privateKey': privateKey,
        }

        try:
            # Generate merchant order ID
            reference = data.get('orderNumber', '')
            _logger.info("Generating merchant order ID for reference: %s", reference)
            merch_order_id = self._generate_telebirr_merch_order_id(reference)
            _logger.info("Generated merchant order ID: %s", merch_order_id)
            amount = data.get('amount')
            _logger.info("Order amount: %s", amount)
            title = self._sanitize_telebirr_title("C2BA"+aggregator_id+"A"+orderNumber)
            _logger.info("Sanitized title: %s", title)

            # Store mapping
            _logger.info("Storing merchant order ID mapping for merch_order_id: %s, reference: %s", merch_order_id, reference)
            self._storeMerchOrderIdMapping("C2BA"+aggregator_id+"A"+orderNumber, amount, pos_ref, sessionId)

            # Get Fabric Token
            _logger.info("Requesting Fabric Token with base_url: %s, fabricAppId: %s", base_url, fabricAppId)
            fabric_token_result = self.applyFabricToken(
                base_url,
                fabricAppId,
                appSecret
            )
            _logger.info("Fabric Token response: %s", fabric_token_result)
            if 'token' not in fabric_token_result:
                _logger.error("Failed to retrieve Fabric Token: %s", fabric_token_result.get('error', 'Unknown error'))
                return {'error': f"Failed to retrieve Fabric Token: {fabric_token_result.get('error', 'Unknown error')}"}

            fabric_token = fabric_token_result['token']
            _logger.info("Fabric token retrieved: %s", fabric_token)

            # Create Order
            _logger.info("Creating Telebirr order with fabric_token, title: %s, amount: %s, merch_order_id: %s", title, amount, merch_order_id)
            create_order_result = self.requestCreateOrder(
                fabric_token, title, amount, "C2BA"+aggregator_id+"A"+orderNumber, telebirr_params
            )
            _logger.info("Create Order response: %s", create_order_result)
            if 'errorCode' in create_order_result:
                _logger.error("Create Order API error: %s - %s", create_order_result['errorCode'], create_order_result['errorMsg'])
                return {
                    'error': f"Create Order API error: {create_order_result['errorCode']} - {create_order_result['errorMsg']}"
                }

            if "biz_content" not in create_order_result:
                _logger.error("Create Order API response missing 'biz_content'")
                return {'error': "Create Order API response is missing 'biz_content'"}

            prepay_id = create_order_result["biz_content"]["prepay_id"]
            _logger.info("Prepay ID from createOrderResult: %s", prepay_id)

            _logger.info("Order registration successful, returning prepay_id: %s", prepay_id)
            return {'prepay_id': prepay_id}
        except Exception as e:
            _logger.error("Error registering Telebirr order: %s", str(e))
            return {'error': str(e)}

    @api.model
    def get_qr_code(self, data):
        """Generate a Telebirr QR code URL for the given prepay ID."""
        _logger.info("Generating Telebirr QR code with data: %s", data)
        telebirr_payment = self.env['telebirrqr.payment'].search([('id', '=', data.get('telebirr_payment_id'))], limit=1)
        if not telebirr_payment:
            _logger.error("No Telebirr payment configuration found for ID: %s", data.get('telebirr_payment_id'))
            return {'error': 'No Telebirr payment configuration found.'}

        prepay_id = data.get('prepay_id')
        if not prepay_id:
            _logger.error("Missing prepay ID in data")
            return {'error': 'Missing prepay ID.'}

        try:
            # Generate QR code URL
            _logger.info("Generating QR code URL with prepay_id: %s, merchantAppId: %s, merchantCode: %s", 
                        prepay_id, telebirr_payment.merchantAppId, telebirr_payment.merchantCode)
            qr_code_url = (
                f"https://superapp.ethiomobilemoney.et:38443/customer/downloadPage/en.html?"
                f"businessType=h5Pay&tradeType=PayByQrCode&appId={telebirr_payment.merchantAppId}& " +
                f"merchCode={telebirr_payment.merchantCode}&prepayId={prepay_id}&" +
                f"language=en_US"
            )
            _logger.info("Generated QR code URL: %s", qr_code_url)

            _logger.info("QR code generation successful, returning qr_code_url")
            return {'qr_code_url': qr_code_url}
        except Exception as e:
            _logger.error("Error generating Telebirr QR code: %s", str(e))
            return {'error': str(e)}

    def _sanitize_telebirr_title(self, title):
        """Sanitize title to meet Telebirr requirements."""
        _logger.info("Sanitizing title: %s", title)
        if not title:
            sanitized_title = "POS_Payment_" + self.createNonceStr()[:10]
            _logger.info("No title provided, generated sanitized title: %s", sanitized_title)
            return sanitized_title

        sanitized = re.sub(r'[^a-zA-Z0-9\s\-_.,]', '', title)
        _logger.info("Sanitized title after regex: %s", sanitized)
        if not sanitized.strip():
            sanitized_title = "POS_Payment_" + self.createNonceStr()[:10]
            _logger.info("Sanitized title is empty, generated new title: %s", sanitized_title)
            return sanitized_title

        sanitized_title = sanitized.strip()[:128]
        _logger.info("Final sanitized title: %s", sanitized_title)
        return sanitized_title

    def _generate_telebirr_merch_order_id(self, reference):
        """Generate Telebirr-compatible merchant order ID."""
        _logger.info("Generating merchant order ID for reference: %s", reference)
        clean_id = "POS" + re.sub(r'[^A-Za-z0-9]', '', reference)
        _logger.info("Cleaned reference: %s", clean_id)
        if clean_id and len(clean_id) >= 8 and len(clean_id) <= 32:
            _logger.info("Using sanitized reference as merch_order_id: %s", clean_id)
            return clean_id
        generated_id = self.createNonceStr()
        _logger.info("Generated new merch_order_id: %s", generated_id)
        return generated_id

    def applyFabricToken(self, base_url, fabricAppId, appSecret):
        """Retrieve Fabric Token from Telebirr API."""
        _logger.info("Applying Fabric Token with base_url: %s, fabricAppId: %s", base_url, fabricAppId)
        headers = {
            "Content-Type": "application/json",
            "X-APP-Key": fabricAppId,
        }
        payload = {"appSecret": appSecret}
        data = json.dumps(payload)
        _logger.info("Payload for Fabric Token: %s", data)
        try:
            _logger.info("Sending POST request to %s/payment/v1/token", base_url)
            response = requests.post(
                url=f"{base_url}/payment/v1/token",
                headers=headers,
                data=data,
                verify=False,
            )
            response.raise_for_status()
            response_json = response.json()
            _logger.info("Fabric Token response: %s", response_json)
            return response_json
        except requests.exceptions.RequestException as e:
            _logger.error("Error during applyFabricToken request: %s", str(e))
            return {"error": str(e)}

    def requestCreateOrder(self, fabric_token, title, amount, merch_order_id, telebirr_payment):
        """Request to create a Telebirr order."""
        _logger.info("Creating Telebirr order with fabric_token: %s, title: %s, amount: %s, merch_order_id: %s",
                    fabric_token, title, amount, merch_order_id)
        headers = {
            "Content-Type": "application/json",
            "X-APP-Key": telebirr_payment['fabricAppId'],
            "Authorization": fabric_token,
        }
        payload = self.createRequestObject(title, amount, merch_order_id, telebirr_payment)
        _logger.info("Order creation payload: %s", payload)
        try:
            _logger.info("Sending POST request to %s/payment/v1/merchant/preOrder", telebirr_payment['base_url'])
            response = requests.post(
                url=f"{telebirr_payment['base_url']}/payment/v1/merchant/preOrder",
                headers=headers,
                data=payload,
                verify=False,
            )
            response_json = response.json()
            _logger.info("Create Order response: %s", response_json)
            return response_json
        except requests.exceptions.RequestException as e:
            _logger.error("Error during requestCreateOrder: %s", str(e))
            return {"error": str(e)}

    def createRequestObject(self, title, amount, merch_order_id, telebirr_payment):
        """Create the request payload for Telebirr order creation."""
        _logger.info("Creating request object for title: %s, amount: %s, merch_order_id: %s", title, amount, merch_order_id)
        if not re.match(r'^[A-Za-z0-9]{8,32}$', merch_order_id):
            _logger.error("Invalid merchant order ID: %s. Must be 8-32 alphanumeric characters", merch_order_id)
            raise ValidationError(_("Merchant Order ID must be 8-32 alphanumeric characters"))

        nonce_str = self.createNonceStr()
        timestamp = self.createTimeStamp()
        _logger.info("Generated nonce_str: %s, timestamp: %s", nonce_str, timestamp)
        req = {
            "nonce_str": nonce_str,
            "method": "payment.preorder",
            "timestamp": timestamp,
            "version": "1.0",
            "biz_content": {
                "notify_url": "http://196.189.44.60:8888/miniapp/merchant_callback",
                "redirect_url": "http://your-redirect-url",
                "business_type": "BuyGoods",
                "trade_type": "Checkout",
                "appid": str(telebirr_payment['merchantAppId']),
                "merch_code": telebirr_payment['merchantCode'],
                "merch_order_id": merch_order_id,
                "title": title,
                # "total_amount": str(amount),
                "total_amount": f"{float(amount):.2f}",
                "trans_currency": "ETB",
                "timeout_express": "120m",
                "payee_identifier": telebirr_payment['merchantCode'],
                "payee_identifier_type": "04",
                "payee_type": "5000",
            },
            "sign_type": "SHA256WithRSA",
        }
        _logger.info("Request object before signing: %s", req)
        req["sign"] = self.sign(req, telebirr_payment['privateKey'])
        _logger.info("Signed request object: %s", req)
        return json.dumps(req)

    def sign(self, request, privateKey):
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

    def createNonceStr(self):
        """Generate a random nonce string."""
        _logger.info("Generating nonce string")
        nonce_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))
        _logger.info("Generated nonce string: %s", nonce_str)
        return nonce_str

    def createTimeStamp(self):
        """Generate a timestamp."""
        _logger.info("Generating timestamp")
        timestamp = str(int(time.time()))
        _logger.info("Generated timestamp: %s", timestamp)
        return timestamp

    def _storeMerchOrderIdMapping(self, original_reference, amount, pos_ref, sessionId):
        """Store the mapping between merch_order_id and reference."""
        _logger.info("Storing merchant order ID mapping: original_reference=%s", original_reference)
        self.env['telebirrqr.payment'].create({
            'trace_no': original_reference,
            'price': amount,
            'orignal_ref': pos_ref,
            'status': 'Pending',
            'session_id': sessionId,
        })
        _logger.info("Stored mapping successfully")