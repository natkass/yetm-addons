/** @odoo-module **/

import { registry } from "@web/core/registry";

const actionRegistry = registry.category("actions");

actionRegistry.add("my_pos_refund_sync", (env, params) => {
    const refundId = params?.refund_id ?? "N/A";
    const invoiceNumber = params?.invoice_number ?? "Unknown";
    const buyerName = params?.buyer_name ?? "N/A";

    console.log(" POS Refund Sync Triggered");
    console.log(" Buyer Name:", buyerName);

    env.services.notification.add(
        `✅ Refund #${invoiceNumber} synced successfully (Buyer: ${buyerName})`,
        {
            type: "success",
            title: "POS Refund Synced",
        }
    );

    return Promise.resolve();
});