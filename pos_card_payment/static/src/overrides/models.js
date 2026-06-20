/** @odoo-module */
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { PaymentCardPay } from '@pos_card_payment/app/payment_cardpay';
import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

register_payment_method('card', PaymentCardPay);

patch(Order.prototype, {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        this.card_payment_receipt_data = "";
        this.signature = "";

        if (options.json) {
            this.set_card_payment_receipt_data(options.json.card_payment_receipt_data);
            this.set_signature(options.json.signature);
        }
    },
    init_from_JSON(json) {
        super.init_from_JSON(json);
        this.set_card_payment_receipt_data(json.card_payment_receipt_data);
        this.set_signature(json.signature);
    },
    export_as_JSON() {
        const jsonResult = super.export_as_JSON();
        jsonResult.card_payment_receipt_data = this.card_payment_receipt_data;
        jsonResult.signature = this.signature;
        return jsonResult;
    },
    set_card_payment_receipt_data(value) {
        this.card_payment_receipt_data = value;
    },
    get_card_payment_receipt_data() {
        return this.card_payment_receipt_data;
    },
    set_signature(value) {
        this.signature = value;
    },
    get_signature() {
        return this.signature;
    },
});