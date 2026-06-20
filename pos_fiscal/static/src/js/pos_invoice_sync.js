/** @odoo-module **/

import { registry } from "@web/core/registry";

const actionRegistry = registry.category("actions");

actionRegistry.add("my_pos_invoice_sync", (env, params) => {
    console.log("🧾 Sync called for invoice:", params.invoice_number);

    env.services.notification.add(`Invoice #${params.invoice_number} synced (Buyer: ${params.buyer_name})`, {
        type: "success",
    });
    return Promise.resolve();
});