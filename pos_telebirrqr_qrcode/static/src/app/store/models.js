/** @odoo-module */

import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymenttelebirrqrQRCode } from "@pos_telebirrqr_qrcode/app/payment_telebirrqr_qrcode";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { qrCodeSrc } from "@point_of_sale/utils";
import { Order, Payment } from "@point_of_sale/app/store/models";
import { TelebirrQRPaymentPopup } from "@pos_telebirrqr_qrcode/app/telebirrqr_payment_popup/telebirrqr_payment_popup";

register_payment_method("telebirrqr_qr_code", PaymenttelebirrqrQRCode);

patch(PaymentScreen.prototype, {
    generateTelebirrQRCodeURL(prepay_id, merchantAppId, merchantCode) {
        if (!prepay_id) {
            console.error("Missing prepay_id");
            return { error: "Missing prepay ID." };
        }

        if (!merchantAppId || !merchantCode) {
            console.error("Missing merchantAppId or merchantCode");
            return { error: "Missing merchant credentials." };
        }

        try {
            const qr_code_url = `https://superapp.ethiomobilemoney.et:38443/customer/downloadPage/en.html?` +
                `businessType=h5Pay&tradeType=PayByQrCode&appId=${encodeURIComponent(merchantAppId)}` +
                `&merchCode=${encodeURIComponent(merchantCode)}&prepayId=${encodeURIComponent(prepay_id)}` +
                `&language=en_US`;

            console.log("Generated QR code URL:", qr_code_url);
            return qr_code_url;
        } catch (error) {
            console.error("Error generating QR code URL:", error);
            return { error: error.message };
        }
    },

    async _finalizeValidation() {
        console.log("_finalizeValidation clicked");
        console.log(this.currentOrder);

        const paymentlines = this.currentOrder.paymentlines;
        const telebirrqrPaymentLine = paymentlines.find(paymentline =>
            paymentline.payment_method && paymentline.payment_method.use_payment_terminal === "telebirrqr"
        );

        if (telebirrqrPaymentLine) {
            const amount = telebirrqrPaymentLine.amount;
            const orderNo = this.currentOrder.uid.replace(/-/g, '');
            const base_url = telebirrqrPaymentLine.payment_method.base_url;
            const web_base_url = telebirrqrPaymentLine.payment_method.web_base_url;
            const fabricAppId = telebirrqrPaymentLine.payment_method.fabricAppId;
            const appSecret = telebirrqrPaymentLine.payment_method.appSecret;
            const merchantAppId = telebirrqrPaymentLine.payment_method.merchantAppId;
            const merchantCode = telebirrqrPaymentLine.payment_method.merchantCode;
            const privateKey = telebirrqrPaymentLine.payment_method.privateKey;
            const aggregator_id = telebirrqrPaymentLine.payment_method.aggregator_id;

            const registerData = {
                pos_ref: this.currentOrder.name,
                amount: amount,
                orderNumber: orderNo,
                base_url: base_url,
                web_base_url: web_base_url,
                fabricAppId: fabricAppId,
                appSecret: appSecret,
                merchantAppId: merchantAppId,
                merchantCode: merchantCode,
                privateKey: privateKey,
                sessionId: this.currentOrder.pos.pos_session.id,
                aggregator_id: aggregator_id,
            };

            const payment_status = await this.orm.call(
                'telebirrqr.payment',
                'find_pay_confirmed_telebirr',
                [[], this.currentOrder.name]
            );

            const { fs_no, rf_no, is_refund } = this.currentOrder;
            const eightDigitRegex = /^\d{8}$/;

            if (
                payment_status?.msg === "Success" ||
                (fs_no && eightDigitRegex.test(fs_no)) ||
                (rf_no && eightDigitRegex.test(rf_no) && is_refund)
            ) {
                return await super._finalizeValidation();
            } else {
                try {
                    const registerResponse = await this.orm.call('pos.payment.method', 'register_order', [registerData]);

                    if (registerResponse && registerResponse.prepay_id) {
                        let qrstr = this.generateTelebirrQRCodeURL(registerResponse.prepay_id, merchantAppId, merchantCode);

                        if (telebirrqrPaymentLine.payment_method.screen_qr) {
                            if (!this.currentOrder.uiState.PaymentScreen) {
                                this.currentOrder.uiState.PaymentScreen = {};
                            }
                            this.currentOrder.uiState.PaymentScreen.onlinePaymentData = {
                                amount: amount,
                                qrCode: qrCodeSrc(qrstr),
                                order: this.currentOrder,
                                base_url: base_url,
                                fabricAppId: fabricAppId,
                                appSecret: appSecret,
                                merchantAppId: merchantAppId,
                                merchantCode: merchantCode,
                                merhanOrderId: "C2BA" + aggregator_id + "A" + orderNo,
                                privateKey: privateKey,
                            };
                            const { confirmed, payload: orderServerOPData } = await this.popup.add(TelebirrQRPaymentPopup, this.currentOrder.uiState.PaymentScreen.onlinePaymentData);

                            if (confirmed) {
                                console.log("Payment confirmed with data:", orderServerOPData);
                                if (orderServerOPData.is_paid) {
                                    telebirrqrPaymentLine.set_payment_status("force_done");
                                }
                                else {
                                    this.env.services.notification.add("Payment failed", {
                                        type: 'warning',
                                        sticky: false,
                                    });
                                    return false;
                                }
                            }
                            else {
                                console.log("Payment cancelled by user.");
                                this.env.services.notification.add("Payment cancelled by user.", {
                                    type: 'warning',
                                    sticky: false,
                                });
                                return false;
                            }
                        } else {
                            this.currentOrder.set_payment_qr_code(qrstr);
                        }
                    } else {
                        console.error("Payment registration error:", registerResponse.error || "Unknown error");
                        this.env.services.notification.add("Error : " + registerResponse.error, {
                            type: 'danger',
                            sticky: false,
                        });
                        return false;
                    }
                } catch (error) {
                    console.error("Error during Telebirr payment processing:", error);
                    this.env.services.notification.add("Error : " + error.message, {
                        type: 'danger',
                        sticky: false,
                    });
                    return false;
                }
            }
        } else {
            console.log("No payment line has use_payment_terminal set to 'telebirrqr'.");
        }

        return await super._finalizeValidation();
    },
});