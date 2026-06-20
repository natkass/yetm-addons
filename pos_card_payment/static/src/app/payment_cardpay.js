/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { jsonrpc } from "@web/core/network/rpc_service";

const REQUEST_TIMEOUT = 10000;

export class PaymentCardPay extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.pollingTimeout = null;
        this.inactivityTimeout = null;
        this.queued = false;
        this.payment_stopped = false;
    }

    send_payment_request(cid) {
        super.send_payment_request(cid);
        return this._card_pay(cid);
    }

    generate_deep_link(genotp, cid) {
        const order = this.pos.get_order();
        const line = order.paymentlines.find((paymentLine) => paymentLine.cid === cid);
        const otprandom = genotp;
        const baseUrl = "https://cardprocessor/normalPurchase";

        const uid = encodeURIComponent(order.uid);
        const amount = encodeURIComponent(line.amount.toFixed(2)); // Ensures two decimal places
        const otp = encodeURIComponent(otprandom);
        const callback = encodeURIComponent(window.location.origin + "/cardpayment/verify");
        const from = encodeURIComponent("zoorya");

        // Build query string with encoded values
        const rawQuery = `ref=${uid}&amount=${amount}&otp=${otp}&callback=${callback}&from=${from}`;

        // Encode the full query string
        const encodedQuery = encodeURIComponent(rawQuery);

        // Build final deep link
        const deepLink = `${baseUrl}?${encodedQuery}`;
        return deepLink;
    }

    async _card_pay(cid) {
        const order = this.pos.get_order();
        var self = this;
        if (order.selected_paymentline.amount < 0) {
            this._show_error(_t('Cannot process transactions with negative amount.'));
        }
        const line = order.paymentlines.find((paymentLine) => paymentLine.cid === cid);
        if (window.Android != undefined) {
            if (window.Android.isAndroidPOS()) {
                try {
                    const newotp = Math.floor(10000 + Math.random() * 90000).toString();

                    // Function to generate a random 5-digit OTP
                    const response = await jsonrpc('/create_payment_card', {
                        price: Number(order.selected_paymentline.amount.toFixed(2)),
                        trace_number: order.uid,
                        otp: newotp
                    });

                    if (response.msg === "Exists") {
                        // Check Android transaction status before proceeding
                        let androidSuccess = false;
                        if (window.Android !== undefined && window.Android.isAndroidPOS()) {
                            try {
                                const androidStatus = window.Android.getTransactionStatus(order.uid);
                                if (androidStatus) {
                                    const status = JSON.parse(androidStatus);
                                    const statusValue = (status.status || '').toLowerCase();
                                    const trxnStatusValue = (status.trxnStatus || '').toLowerCase();
                                    if (statusValue === 'success' || trxnStatusValue === 'success') {
                                        line.set_payment_status('done');
                                        return true;
                                    }
                                }
                            } catch (error) {
                                console.error('Error checking Android transaction status:', error);
                                // Continue with deep link if Android check fails
                            }
                        }
                        // If not success, proceed as before
                        //update status to retry
                        const change_status = await jsonrpc('/change_status', {
                            trace_number: order.uid,
                            status: 'Retry',
                        });
                        if (change_status) {
                            console.log(
                                "OTP already exists, but the payment is not confirmed. Generating a new OTP and setting retry status to retry."
                            );
                            console.log(this.generate_deep_link(response.otp, cid));
                            window.Android.openDeepLink(this.generate_deep_link(response.otp, cid));
                        }
                    } else if (response.msg === "Created") {
                        window.Android.openDeepLink(this.generate_deep_link(newotp, cid));
                    } else if (response.msg === "Error") {
                        console.error("Error occurred while creating payment entry:", response.error);
                        this.env.services.notification.add("Payment creation failed: " + response.error, {
                            type: 'danger',
                            sticky: false,
                            timeout: 10000,
                        });
                        line.set_payment_status('retry');
                        return false;
                    }
                } catch (error) {
                    line.set_payment_status('retry');
                    console.error('Error occurred while sending data:', error);
                    this.env.services.notification.add("Unexpected error: " + error.message, {
                        type: 'danger',
                        sticky: false,
                        timeout: 10000,
                    });
                    return false;
                }
                return self.cardpay_handle_response(cid);
            }
        }
        else {
            this.env.services.notification.add("Invalid Device", {
                type: 'danger',
                sticky: false,
                timeout: 10000,
            });
            return false;
        }
    }

    cardpay_handle_response(cid) {
        var line = this.pos.get_order().selected_paymentline;
        line.set_payment_status('waitingCard');

        var self = this;
        var res = new Promise(function (resolve, reject) {

            clearTimeout(self.polling);

            self.polling = setInterval(function () {
                self._poll_for_response(resolve, reject, cid);
            }, 3000);
        });

        res.finally(function () {
            self._reset_state();
        });
        return res;
    }

    _poll_for_response(resolve, reject, cid) {
        var self = this;
        var line = this.pos.get_order().paymentlines.find((paymentLine) => paymentLine.cid === cid);

        // Check if `line` exists before accessing its properties
        if (!line) {
            console.log("Payment line does not exist. Resolving the promise.");
            resolve(false); // Resolve the promise if `line` is undefined
            return Promise.resolve();
        }

        console.log("STATUS : " + line.get_payment_status());

        // Proceed only if the payment status is 'waitingCard'
        if (line.get_payment_status() !== 'waitingCard') {
            resolve(false);
            return Promise.resolve();
        }

        // First check status using Android WebView if available
        if (window.Android !== undefined && window.Android.isAndroidPOS()) {
            try {
                const androidStatus = window.Android.getTransactionStatus(self.pos.get_order().uid);
                console.log("androidStatus : " + androidStatus);
                if (androidStatus) {
                    const status = JSON.parse(androidStatus);
                    const statusValue = (status.status || '').toLowerCase();
                    const trxnStatusValue = (status.trxnStatus || '').toLowerCase();
                    if (statusValue === 'success' || trxnStatusValue === 'success') {
                        var order = self.pos.get_order();
                        // Try to parse trxnData if present
                        let receiptData = {};
                        if (status.trxnData) {
                            try {
                                receiptData = JSON.parse(status.trxnData);
                            } catch (e) {
                                receiptData = status.trxnData;
                            }
                        }
                        order.set_card_payment_receipt_data(receiptData);
                        order.set_signature(receiptData.signature || status.signature || '');
                        return resolve(true);
                    } else if (statusValue === 'failed' || trxnStatusValue === 'failed') {
                        var order = self.pos.get_order();
                        // Try to parse trxnData if present
                        let receiptData = {};
                        if (status.trxnData) {
                            try {
                                receiptData = JSON.parse(status.trxnData);
                            } catch (e) {
                                receiptData = status.trxnData;
                            }
                        }
                        order.set_card_payment_receipt_data(receiptData);
                        order.set_signature(receiptData.signature || status.signature || '');
                        line.set_payment_status('retry');
                        return reject();
                    }
                    // If status is pending or undefined, continue with ORM call
                }
            } catch (error) {
                console.error('Error checking Android transaction status:', error);
                // Continue with ORM call if Android check fails
            }
        }

        // Define a function to make the ORM call
        function makeOrmCall() {
            return self.env.services.orm.silent.call(
                'cardpay.payment.status',
                'find_pay_confirmed_card',

                [[self.payment_method.id], self.pos.get_order().uid]
            );
        }

        // Create a promise that resolves when either the ORM call resolves or the timeout is reached
        var timeoutPromise = new Promise(function (resolve, reject) {
            setTimeout(function () {
                reject();
            }, 5000);
        });

        return Promise.race([makeOrmCall(), timeoutPromise])
            .then(function (status) {
                if (status) {
                    var order = self.pos.get_order();
                    var line = order.selected_paymentline;
                    if (status.msg !== '') {
                        if (status.msg == 'Success') {
                            order.set_card_payment_receipt_data(status.receiptData);
                            order.set_signature(status.signature);
                            return resolve(true);
                        }
                        else if (status.msg == 'Failed') {
                            order.set_card_payment_receipt_data(status.receiptData);
                            order.set_signature(status.signature);
                            line.set_payment_status('retry');
                            reject();
                        }
                    } else if (status.msg == '') {
                        self._show_error(_t('The connection to your payment terminal failed. Please check if it is still connected to the internet.'));
                        self._cardpay_cancel();
                        resolve(false);
                    }
                }
            })
            .catch(function (error) {
                if (self.remaining_polls != 0) {
                    self.remaining_polls--;
                } else {
                    reject();
                    self.poll_error_order = self.pos.get_order();
                    return self._handle_odoo_connection_failure(error);
                }
                throw error;
            });
    }

    _cardpay_cancel() {
        this._reset_state();
        var order = this.pos.get_order();
        var line = order.selected_paymentline;
        if (line) {
            line.set_payment_status('retry');
        }
        return Promise.reject();
    }

    _show_error(msg, title) {
        if (!title) {
            title = _t('Card Payment Error');
        }
        Gui.showPopup('ErrorPopup', {
            'title': title,
            'body': msg,
        });
    }

    _reset_state() {
        clearTimeout(this.polling);
    }

    pending_razorpay_line() {
        return this.pos.getPendingPaymentLine("card");
    }

    send_payment_cancel(order, cid) {
        super.send_payment_cancel(order, cid);
        return this._cardpay_cancel();
    }

    _handle_odoo_connection_failure(data = {}) {
        // handle timeout
        const line = this.pending_razorpay_line();
        if (line) {
            line.set_payment_status("retry");
        }
        this._showError(
            _t(
                "Could not connect to the Odoo server, please check your internet connection and try again."
            )
        );

        return Promise.reject(data); // prevent subsequent onFullFilled's from being called
    }

    _stop_pending_payment() {
        return new Promise(resolve => this.inactivityTimeout = setTimeout(resolve, 90000));
    }

    _removePaymentHandler(payment_data) {
        payment_data.forEach((data) => {
            localStorage.removeItem(data);
        })
        clearTimeout(this.pollingTimeout);
        clearTimeout(this.inactivityTimeout);
        this.queued = this.payment_stopped = false;
    }

    _showError(error_msg, title) {
        this.env.services.dialog.add(AlertDialog, {
            title: title || _t("Card Payment Error"),
            body: error_msg,
        });
    }
}