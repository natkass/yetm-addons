/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { useService } from "@web/core/utils/hooks";
import { jsonrpc } from "@web/core/network/rpc_service";

export class TelebirrQRPaymentPopup extends AbstractAwaitablePopup {
    static template = "pos_telebirrqr_qrcode.TelebirrQRPaymentPopup";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.pollingActive = true;

        if (this.props.order.uiState.PaymentScreen) {
            this.props.order.uiState.PaymentScreen.telebirrQRPaymentPopup = this;
        }

        this.startPolling();
    }

    async startPolling() {
        const poll = async () => {
            if (!this.pollingActive) return;

            try {
                // First check using ORM (telebirrqr.payment Model) call to see if payment is confirmed
                const firstCheckResult = await this.orm.call(
                    'telebirrqr.payment',
                    'find_pay_confirmed_telebirr',
                    [[], this.props.order.name]
                );
                if (firstCheckResult?.msg === "Success") {
                    this.pollingActive = false;
                    this.setReceivedOrderServerOPData({ is_paid: true });
                } else if (firstCheckResult?.msg === "Failed") {
                    this.pollingActive = false;
                    this.env.services.notification.add("Payment failed. Please try again.", {
                        type: "danger",
                    });
                    this.cancel();
                } else {
                    const urlObj = new URL(this.props.base_url);
                    const baseHost = `${urlObj.protocol}//${urlObj.host}`;
                    // Continue to polling directly to Telebirr API
                    const payload = {
                        base_url: baseHost + "/apiaccess/payment/gateway",
                        fabric_app_id: this.props.fabricAppId,
                        app_secret: this.props.appSecret,
                        merchant_app_id: this.props.merchantAppId,
                        merchant_code: this.props.merchantCode,
                        merch_order_id: this.props.merhanOrderId,
                        private_key: this.props.privateKey,
                    };

                    const result = await jsonrpc('/query_status', payload);

                    setTimeout(poll, 2000);
                    console.log("Polling result:", result);

                    if (result.result === "SUCCESS") {
                        if (result.biz_content?.order_status === "PAY_SUCCESS") {
                            this.pollingActive = false;
                            this.setReceivedOrderServerOPData({ is_paid: true });
                        } else {
                            setTimeout(poll, 2000);
                        }
                    } else {
                        // Failed to get success from endpoint
                        this.pollingActive = false;
                        this.env.services.notification.add(result.message || "Payment check failed.", {
                            type: "danger",
                        });
                        this.cancel();
                    }
                }
            } catch (err) {
                console.error("Polling error:", err);
                setTimeout(poll, 2000);
            }
        };

        poll();
    }

    setReceivedOrderServerOPData(opData) {
        this.opData = opData;
        this.confirm();
    }

    async confirm() {
        this.pollingActive = false;
        super.confirm();
        delete this.props.order.uiState.PaymentScreen?.telebirrQRPaymentPopup;
    }

    cancel() {
        this.pollingActive = false;
        super.cancel();
        delete this.props.order.uiState.PaymentScreen?.telebirrQRPaymentPopup;
    }

    async getPayload() {
        return this.opData;
    }
}