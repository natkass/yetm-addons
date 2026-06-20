/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SaleOrderManagementScreen } from "@pos_sale/app/order_management_screen/sale_order_management_screen/sale_order_management_screen";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { _t } from "@web/core/l10n/translation";
import { Orderline } from "@point_of_sale/app/store/models";
import { floatIsZero } from "@web/core/utils/numbers";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";

patch(SaleOrderManagementScreen.prototype, {
    async onClickSaleOrder(clickedOrder) {
        const { confirmed, payload: selectedOption } = await this.popup.add(SelectionPopup, {
            title: _t("What do you want to do?"),
            list: [
                { id: "0", label: _t("Settle the order"), item: "settle" }
            ],
        });

        if (confirmed) {
            let currentPOSOrder = this.pos.get_order();
            const sale_order = await this._getSaleOrder(clickedOrder.id);
            clickedOrder.shipping_date = this.pos.config.ship_later && sale_order.shipping_date;

            const currentSaleOrigin = this._getSaleOrderOrigin(currentPOSOrder);
            const currentSaleOriginId = currentSaleOrigin && currentSaleOrigin.id;

            if (currentSaleOriginId) {
                const linkedSO = await this._getSaleOrder(currentSaleOriginId);
                if (
                    getId(linkedSO.partner_id) !== getId(sale_order.partner_id) ||
                    getId(linkedSO.partner_invoice_id) !== getId(sale_order.partner_invoice_id) ||
                    getId(linkedSO.partner_shipping_id) !== getId(sale_order.partner_shipping_id)
                ) {
                    currentPOSOrder = this.pos.add_new_order();
                    this.notification.add(_t("A new order has been created."), 4000);
                }
            }

            try {
                await this.pos.load_new_partners();
            } catch {
                // FIXME Universal catch seems ill advised
            }
            const order_partner = this.pos.db.get_partner_by_id(sale_order.partner_id[0]);
            if (order_partner) {
                currentPOSOrder.set_partner(order_partner);
            } else {
                try {
                    await this.pos._loadPartners([sale_order.partner_id[0]]);
                } catch {
                    const title = _t("Customer loading error");
                    const body = _t(
                        "There was a problem in loading the %s customer.",
                        sale_order.partner_id[1]
                    );
                    await this.popup.add(ErrorPopup, { title, body });
                }
                currentPOSOrder.set_partner(
                    this.pos.db.get_partner_by_id(sale_order.partner_id[0])
                );
            }
            const orderFiscalPos = sale_order.fiscal_position_id
                ? this.pos.fiscal_positions.find(
                    (position) => position.id === sale_order.fiscal_position_id[0]
                )
                : false;
            if (orderFiscalPos) {
                currentPOSOrder.fiscal_position = orderFiscalPos;
            }
            const orderPricelist = sale_order.pricelist_id
                ? this.pos.pricelists.find(
                    (pricelist) => pricelist.id === sale_order.pricelist_id[0]
                )
                : false;
            if (orderPricelist) {
                currentPOSOrder.set_pricelist(orderPricelist);
            }

            if (selectedOption == "settle") {
                const lines = sale_order.order_line;
                this.pos.get_order().set_plate_no(sale_order.x_studio_final_reg);
                this.pos.get_order().set_chassis_no(sale_order.x_studio_chassis_final);
                this.pos.get_order().set_job_card_no(sale_order.repair_job_card);
                this.pos.get_order().set_tamrin_payment_type(sale_order.x_studio_method_of_payment);
                // this.pos.get_order().set_brand(sale_order.x_studio_brand_finall);
                // this.pos.get_order().set_model(sale_order.x_studio_model_finalll);

                if (sale_order.x_studio_brand_finall && sale_order.x_studio_brand_finall[1]) {
                    this.pos.get_order().set_brand(sale_order.x_studio_brand_finall[1]);
                } else {
                    this.pos.get_order().set_brand(null); // Or an appropriate fallback value
                }
                
                if (sale_order.x_studio_model_finalll && sale_order.x_studio_model_finalll[1]) {
                    this.pos.get_order().set_model(sale_order.x_studio_model_finalll[1]);
                } else {
                    this.pos.get_order().set_model(null); // Or an appropriate fallback value
                }

                console.dir("=== sale_order ===");
                console.dir(sale_order);

                const product_to_add_in_pos = lines
                    .filter((line) => !this.pos.db.get_product_by_id(line.product_id[0]))
                    .map((line) => line.product_id[0]);

                if (product_to_add_in_pos.length) {
                    const { confirmed } = await this.popup.add(ConfirmPopup, {
                        title: _t("Products not available in POS"),
                        body: _t(
                            "Some of the products in your Sale Order are not available in POS, do you want to import them?"
                        ),
                        confirmText: _t("Yes"),
                        cancelText: _t("No"),
                    });
                    if (confirmed) {
                        await this.pos._addProducts(product_to_add_in_pos);
                    }
                }

                /**
                 * This variable will have 3 values, `undefined | false | true`.
                 * Initially, it is `undefined`. When looping thru each sale.order.line,
                 * when a line comes with lots (`.lot_names`), we use these lot names
                 * as the pack lot of the generated pos.order.line. We ask the user
                 * if he wants to use the lots that come with the sale.order.lines to
                 * be used on the corresponding pos.order.line only once. So, once the
                 * `useLoadedLots` becomes true, it will be true for the succeeding lines,
                 * and vice versa.
                 */
                let useLoadedLots;

                for (var i = 0; i < lines.length; i++) {
                    const line = lines[i];
                    if (!this.pos.db.get_product_by_id(line.product_id[0])) {
                        continue;
                    }

                    const line_values = {
                        pos: this.pos,
                        order: this.pos.get_order(),
                        product: this.pos.db.get_product_by_id(line.product_id[0]),
                        description: line.name,
                        price: line.price_unit,
                        tax_ids: orderFiscalPos ? undefined : line.tax_id,
                        price_manually_set: false,
                        sale_order_origin_id: clickedOrder,
                        sale_order_line_id: line,
                        customer_note: line.customer_note,
                    };

                    const new_line = new Orderline({ env: this.env }, line_values);

                    if (
                        new_line.get_product().tracking !== "none" &&
                        (this.pos.picking_type.use_create_lots ||
                            this.pos.picking_type.use_existing_lots) &&
                        line.lot_names.length > 0
                    ) {
                        const { confirmed } =
                            useLoadedLots === undefined
                                ? await this.popup.add(ConfirmPopup, {
                                    title: _t("SN/Lots Loading"),
                                    body: _t(
                                        "Do you want to load the SN/Lots linked to the Sales Order?"
                                    ),
                                    confirmText: _t("Yes"),
                                    cancelText: _t("No"),
                                })
                                : { confirmed: useLoadedLots };
                        useLoadedLots = confirmed;

                        if (useLoadedLots) {
                            const lot_lines = (line.lot_names || []).map((name) => ({ lot_name: name }));
                            new_line.setPackLotLines({
                                modifiedPackLotLines: [],
                                newPackLotLines: lot_lines,
                            });
                        }
                    }

                    new_line.setQuantityFromSOL(line);

                    new_line.set_unit_price(line.price_unit);

                    new_line.set_discount(line.discount);

                    const product = this.pos.db.get_product_by_id(line.product_id[0]);
                    const product_unit = product.get_unit();

                    if (product_unit && !product.get_unit().is_pos_groupable) {
                        let remaining_quantity = new_line.quantity;
                        while (!floatIsZero(remaining_quantity, 6)) {

                            const splitted_line = new Orderline({ env: this.env }, line_values);
                            splitted_line.set_quantity(Math.min(remaining_quantity, 1.0), true);
                            this.pos.get_order().add_orderline(splitted_line);

                            remaining_quantity -= splitted_line.quantity;
                        }
                    } else {
                        this.pos.get_order().add_orderline(new_line);
                    }
                }
            }

            this.pos.closeScreen();
        }
    },
    async _getSaleOrder(id) {
        const [sale_order] = await this.orm.read(
            "sale.order",
            [id],
            [
                "order_line",
                "partner_id",
                "pricelist_id",
                "fiscal_position_id",
                "amount_total",
                "amount_untaxed",
                "amount_unpaid",
                "picking_ids",
                "partner_shipping_id",
                "partner_invoice_id",
                "x_studio_final_reg",
                "x_studio_model_finalll",
                "x_studio_brand_finall",
                "x_studio_chassis_final",
                "repair_job_card_id",
                "branch",
                "x_studio_method_of_payment"
            ]
        );

        const sale_lines = await this._getSOLines(sale_order.order_line);
        sale_order.order_line = sale_lines;

        if (sale_order.picking_ids[0]) {
            const [picking] = await this.orm.read(
                "stock.picking",
                [sale_order.picking_ids[0]],
                ["scheduled_date"]
            );
            sale_order.shipping_date = picking.scheduled_date;
        }

        sale_order.repair_job_card = "";
        if (sale_order.repair_job_card_id) {
            sale_order.repair_job_card = sale_order.repair_job_card_id[1];
        }

        return sale_order;
    }

});