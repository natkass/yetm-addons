/** @odoo-module **/

import { Component, useEnv } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PosDeviceSync extends Component {
    setup() {
        this.orm = useService("orm");
        this.env = useEnv();
    }

    convertDateFormat(dateStr) {
        const parts = dateStr.split("/");
        if (parts.length === 3) {
            return `${parts[2]}-${parts[1].padStart(2, "0")}-${parts[0].padStart(2, "0")}`;
        }
        return dateStr;
    }

    async syncDevice() {
        if (typeof window.Android === "undefined" ||
            typeof window.Android.getInvoicesAfterFsNumber !== "function" ||
            typeof window.Android.getRefundInvoicesAfterRfdNumber !== "function" ||
            typeof window.Android.getZReportsAfterZNumber !== "function") {
            this.env.services.notification.add(`This operation is only allowed from a POS device.`, {
                type: "info",
            });
            console.error("This operation is only allowed from a POS device.");
            return;
        }

        var result = await window.Android.getMachineData();
        var resObj = JSON.parse(result);

        var fiscalInfo = resObj["fiscalInfo"];
        var mrc = fiscalInfo.split(",")[1];

        const deviceIds = await this.orm.search("pos.device", [["mrc", "=", mrc]], { limit: 1 });
        if (!deviceIds.length) {
            this.env.services.notification.add(`No POS device found with MRC ${mrc}`, {
                type: "info",
            });
            return;
        }
        const deviceId = deviceIds[0];

        let [device] = await this.orm.read("pos.device", [deviceId], ["id", "mrc", "name"]);

        let syncedInvoices = 0;
        let syncedRefunds = 0;
        let syncedZReports = 0;
        let maxFsNo = 0;
        let maxRfdNo = 0;
        let maxZNo = 0;

        // --- Get max sync values from server ---
        const maxValues = await this.orm.call(
            "pos.device",
            "get_device_max_sync_values",
            [deviceId]
        );
        maxFsNo = maxValues.max_fs_number || 0;
        maxRfdNo = maxValues.max_rfd_number || 0;
        maxZNo = maxValues.max_z_number || 0;

        console.log(`Starting invoice sync from fsNumber ${maxFsNo} for device ${device.mrc}`);

        while (true) {
            const result = window.Android.getInvoicesAfterFsNumber(
                JSON.stringify({ fs_number: maxFsNo }),
                device.mrc
            );

            let invoices;
            try {
                invoices = JSON.parse(result);
            } catch (e) {
                this.env.services.notification.add("Failed to parse invoice data from Android device.", {
                    type: "danger",
                });
                console.error(e);
                break;
            }

            if (!invoices || invoices.length === 0) break;

            for (const invoice of invoices) {
                const existingInvoice = await this.orm.search(
                    "pos.invoice",
                    [["fsNumber", "=", invoice.fsNumber], ["device_id", "=", deviceId]],
                    { limit: 1 }
                );
                if (existingInvoice.length > 0) {
                    console.log(`Skipping duplicate invoice with fsNumber ${invoice.fsNumber}`);
                    maxFsNo = Math.max(maxFsNo, invoice.fsNumber);
                    continue;
                }

                const lines = (invoice.lines || []).map(line => ({
                    lineIndex: line.lineIndex,
                    pluCode: line.pluCode,
                    itemName: line.itemName,
                    itemShortName: line.itemShortName,
                    itemDescription: line.itemDescription,
                    quantity: line.quantity,
                    unit_name: line.unit_name,
                    price: line.price,
                    lineDiscount: line.lineDiscount,
                    lineDiscountAmount: line.lineDiscountAmount,
                    lineDiscountType: line.lineDiscountType,
                    lineServiceCharge: line.lineServiceCharge,
                    lineServiceChargeAmount: line.lineServiceChargeAmount,
                    lineServiceChargeType: line.lineServiceChargeType,
                    date: this.convertDateFormat(line.date),
                    time: line.time,
                    lineTotal: line.lineTotal,
                    lineTotalTax: line.lineTotalTax,
                    lineTotalWithTax: line.lineTotalWithTax,
                    taxAmount: line.taxAmount,
                    taxRate: line.taxRate,
                    isVoided: line.isVoided,
                }));

                const invoiceVals = {
                    fsNumber: invoice.fsNumber,
                    referenceNumber: invoice.referenceNumber,
                    paymentType: invoice.paymentType,
                    paymentReferenceNumber: invoice.paymentReferenceNumber,
                    buyerName: invoice.buyerName,
                    buyerTradeName: invoice.buyerTradeName,
                    buyerTaxIdNumber: invoice.buyerTaxIdNumber,
                    buyerPhoneNumber: invoice.buyerPhoneNumber,
                    cashierName: invoice.cashierName,
                    headerMemo: invoice.headerMemo,
                    footerMemo: invoice.footerMemo,
                    checksum: invoice.timeStamp,
                    remark: invoice.remark,
                    approvedBy: invoice.approvedBy,
                    totalWithoutTax: invoice.totalWithoutTax,
                    totalTax: invoice.totalTax,
                    totalTaxabl1: invoice.totalTaxabl1,
                    totalTax1: invoice.totalTax1,
                    totalTaxabl2: invoice.totalTaxabl2,
                    totalTax2: invoice.totalTax2,
                    totalTaxabl3: invoice.totalTaxabl3,
                    totalTax3: invoice.totalTax3,
                    totalNonTax: invoice.totalNonTax,
                    totalWithTax: invoice.totalWithTax,
                    totalPaid: invoice.totalPaid,
                    totalDiscount: invoice.totalDiscount,
                    totalServiceCharge: invoice.totalServiceCharge,
                    total: invoice.total,
                    change: invoice.change,
                    zReportSent: invoice.zReportSent,
                    printed: invoice.printed,
                    date: this.convertDateFormat(invoice.date),
                    time: invoice.time,
                    qrCodeData: invoice.qrCodeData,
                    itemCount: invoice.itemCount,
                    zNo: invoice.zNo,
                    globalDiscountType: invoice.globalDiscountType,
                    globalDiscountAmount: invoice.globalDiscountAmount,
                    globalServiceChargeType: invoice.globalServiceChargeType,
                    globalServiceChargeAmount: invoice.globalServiceChargeAmount,
                    printCopy: invoice.printCopy,
                    ejPath: invoice.ejPath,
                    device_id: deviceId,
                    line_ids: lines.map(line => [0, 0, line]),
                };

                await this.orm.create("pos.invoice", [invoiceVals]);
                maxFsNo = Math.max(maxFsNo, invoice.fsNumber);
                syncedInvoices++;
            }
        }

        // --- Sync Refunds ---
        console.log(`Starting refund sync from rfdNumber ${maxRfdNo} for device ${device.mrc}`);

        while (true) {
            const result = window.Android.getRefundInvoicesAfterRfdNumber(
                JSON.stringify({ rfd_number: maxRfdNo }),
                device.mrc
            );

            let refunds;
            try {
                refunds = JSON.parse(result);
            } catch (e) {
                this.env.services.notification.add("Failed to parse refund invoice data from Android device.", {
                    type: "danger",
                });
                console.error(e);
                break;
            }

            if (!refunds || refunds.length === 0) break;

            for (const refund of refunds) {
                const existingRefund = await this.orm.search(
                    "pos.refund",
                    [["rfdNumber", "=", refund.rfdNumber], ["device_id", "=", deviceId]],
                    { limit: 1 }
                );
                if (existingRefund.length > 0) {
                    console.log(`Skipping duplicate refund with rfdNumber ${refund.rfdNumber}`);
                    maxRfdNo = Math.max(maxRfdNo, refund.rfdNumber);
                    continue;
                }

                const lines = (refund.lines || []).map(line => ({
                    lineIndex: line.lineIndex,
                    itemName: line.itemName,
                    itemShortName: line.itemShortName,
                    itemDescription: line.itemDescription,
                    quantity: line.quantity,
                    unit_name: line.unit_name,
                    price: line.price,
                    lineDiscount: line.lineDiscount,
                    lineDiscountAmount: line.lineDiscountAmount,
                    lineDiscountType: line.lineDiscountType,
                    lineServiceCharge: line.lineServiceCharge,
                    lineServiceChargeAmount: line.lineServiceChargeAmount,
                    lineServiceChargeType: line.lineServiceChargeType,
                    lineTotal: line.lineTotal,
                    lineTotalTax: line.lineTotalTax,
                    lineTotalWithTax: line.lineTotalWithTax,
                    taxAmount: line.taxAmount,
                    taxRate: line.taxRate,
                }));

                const refundVals = {
                    rfdNumber: refund.rfdNumber,
                    referenceNumber: refund.referenceNumber,
                    paymentType: refund.paymentType,
                    paymentReferenceNumber: refund.paymentReferenceNumber,
                    buyerName: refund.buyerName,
                    buyerTradeName: refund.buyerTradeName,
                    buyerTaxIdNumber: refund.buyerTaxIdNumber,
                    buyerPhoneNumber: refund.buyerPhoneNumber,
                    cashierName: refund.cashierName,
                    headerMemo: refund.headerMemo,
                    footerMemo: refund.footerMemo,
                    checksum: refund.timeStamp,
                    remark: refund.remark,
                    approvedBy: refund.approvedBy,
                    totalWithoutTax: refund.totalWithoutTax,
                    totalTax: refund.totalTax,
                    totalTaxabl1: refund.totalTaxabl1,
                    totalTax1: refund.totalTax1,
                    totalTaxabl2: refund.totalTaxabl2,
                    totalTax2: refund.totalTax2,
                    totalTaxabl3: refund.totalTaxabl3,
                    totalTax3: refund.totalTax3,
                    totalNonTax: refund.totalNonTax,
                    totalWithTax: refund.totalWithTax,
                    totalPaid: refund.totalPaid,
                    totalDiscount: refund.totalDiscount,
                    totalServiceCharge: refund.totalServiceCharge,
                    total: refund.total,
                    change: refund.change,
                    zReportSent: refund.zReportSent,
                    printed: refund.printed,
                    date: this.convertDateFormat(refund.date),
                    time: refund.time,
                    qrCodeData: refund.qrCodeData,
                    itemCount: refund.itemCount,
                    zNo: refund.zNo,
                    globalDiscountType: refund.globalDiscountType,
                    globalDiscountAmount: refund.globalDiscountAmount,
                    globalServiceChargeType: refund.globalServiceChargeType,
                    globalServiceChargeAmount: refund.globalServiceChargeAmount,
                    commercialLogo: refund.commercialLogo,
                    printCopy: refund.printCopy,
                    ejPath: refund.ejPath,
                    device_id: deviceId,
                    line_ids: lines.map(line => [0, 0, line]),
                };

                await this.orm.create("pos.refund", [refundVals]);
                maxRfdNo = Math.max(maxRfdNo, refund.rfdNumber);
                syncedRefunds++;
            }
        }

        // --- Sync Z Reports ---
        console.log(`Starting Z report sync from zNumber ${maxZNo} for device ${device.mrc}`);

        while (true) {
            const result = window.Android.getZReportsAfterZNumber(
                JSON.stringify({ z_number: maxZNo }),
                device.mrc
            );

            let zReports;
            try {
                zReports = JSON.parse(result);
            } catch (e) {
                this.env.services.notification.add("Failed to parse Z report data from Android device.", {
                    type: "danger",
                });
                console.error(e);
                break;
            }

            if (!zReports || zReports.length === 0) break;

            for (const zReport of zReports) {
                const existingZReport = await this.orm.search(
                    "pos.zreport",
                    [["zNumber", "=", zReport.zNumber], ["device_id", "=", deviceId]],
                    { limit: 1 }
                );
                if (existingZReport.length > 0) {
                    console.log(`Skipping duplicate Z report with zNumber ${zReport.zNumber}`);
                    maxZNo = Math.max(maxZNo, zReport.zNumber);
                    continue;
                }

                const zReportVals = {
                    zNumber: zReport.zNumber,
                    txbl1: zReport.txbl1,
                    txbl2: zReport.txbl2,
                    txbl3: zReport.txbl3,
                    notxbl: zReport.notxbl,
                    tax1: zReport.tax1,
                    tax1Val: zReport.tax1Val,
                    tax2: zReport.tax2,
                    tax2Val: zReport.tax2Val,
                    tax3: zReport.tax3,
                    tax3Val: zReport.tax3Val,
                    salesTotal: zReport.salesTotal,
                    txblTotal: zReport.txblTotal,
                    taxTotal: zReport.taxTotal,
                    rfdTxbl1: zReport.rfdTxbl1,
                    rfdTxbl2: zReport.rfdTxbl2,
                    rfdTxbl3: zReport.rfdTxbl3,
                    rfdNotxbl: zReport.rfdNotxbl,
                    rfdTax1: zReport.rfdTax1,
                    rfdTax2: zReport.rfdTax2,
                    rfdTax3: zReport.rfdTax3,
                    rfdSalesTotal: zReport.rfdSalesTotal,
                    rfdTxblTotal: zReport.rfdTxblTotal,
                    rfdTaxTotal: zReport.rfdTaxTotal,
                    accumulatedFs: zReport.accumulatedFs,
                    lastReceiptDate: zReport.lastReceiptDate && zReport.lastReceiptDate.trim() !== '' ? this.convertDateFormat(zReport.lastReceiptDate) : null,
                    lastReceiptTime: zReport.lastReceiptTime && zReport.lastReceiptTime.trim() !== '' ? zReport.lastReceiptTime : null,
                    lastFsNo: zReport.lastFsNo,
                    sessionFSCount: zReport.sessionFSCount,
                    accumulatedNfNo: zReport.accumulatedNfNo,
                    sessionNFCount: zReport.sessionNFCount,
                    accumulatedRfd: zReport.accumulatedRfd,
                    sessionRfdCount: zReport.sessionRfdCount,
                    sessionResetCount: zReport.sessionResetCount,
                    savedOnERCAFtp: zReport.savedOnERCAFtp,
                    date: this.convertDateFormat(zReport.date),
                    time: zReport.time,
                    checksum: zReport.timeStamp,
                    ejPath: zReport.ejPath,
                    isPrinted: zReport.isPrinted,
                    toBePrint: zReport.toBePrint,
                    device_id: deviceId,
                };

                await this.orm.create("pos.zreport", [zReportVals]);
                maxZNo = Math.max(maxZNo, zReport.zNumber);
                syncedZReports++;
            }
        }

        this.env.services.notification.add(
            `${syncedInvoices} invoices, ${syncedRefunds} refunds, and ${syncedZReports} Z reports synced successfully.`,
            { type: "success" }
        );
    }

    // async syncDevice() {
    //     if (typeof window.Android === "undefined" ||
    //         typeof window.Android.getInvoicesAfterFsNumber !== "function" ||
    //         typeof window.Android.getRefundInvoicesAfterRfdNumber !== "function" ||
    //         typeof window.Android.getZReportsAfterZNumber !== "function") {
    //         this.env.services.notification.add(`This operation is only allowed from a POS device.`, {
    //             type: "info",
    //         });
    //         console.error("This operation is only allowed from a POS device.");
    //         return;
    //     }

    //     const deviceId = this.props.record.evalContextWithVirtualIds.id;
    //     let [device] = await this.orm.read("pos.device", [deviceId], ["id", "mrc", "name"]);

    //     let syncedInvoices = 0;
    //     let syncedRefunds = 0;
    //     let syncedZReports = 0;
    //     let maxFsNo = 0;
    //     let maxRfdNo = 0;
    //     let maxZNo = 0;

    //     // --- Sync Invoices ---
    //     const [lastInvoiceId] = await this.orm.search(
    //         "pos.invoice",
    //         [["device_id", "=", deviceId]],
    //         { order: "fsNumber desc", limit: 1 }
    //     );
    //     if (lastInvoiceId) {
    //         const [lastInvoice] = await this.orm.read("pos.invoice", [lastInvoiceId], ["fsNumber"]);
    //         maxFsNo = lastInvoice.fsNumber || 0;
    //     }

    //     console.log(`Starting invoice sync from fsNumber ${maxFsNo} for device ${device.mrc}`);

    //     while (true) {
    //         const result = window.Android.getInvoicesAfterFsNumber(
    //             JSON.stringify({ fs_number: maxFsNo }),
    //             device.mrc
    //         );

    //         let invoices;
    //         try {
    //             invoices = JSON.parse(result);
    //         } catch (e) {
    //             this.env.services.notification.add("Failed to parse invoice data from Android device.", {
    //                 type: "danger",
    //             });
    //             console.error(e);
    //             break;
    //         }

    //         if (!invoices || invoices.length === 0) break;

    //         for (const invoice of invoices) {
    //             // Check for existing invoice by fsNumber
    //             const existingInvoice = await this.orm.search(
    //                 "pos.invoice",
    //                 [["fsNumber", "=", invoice.fsNumber], ["device_id", "=", deviceId]],
    //                 { limit: 1 }
    //             );
    //             if (existingInvoice.length > 0) {
    //                 console.log(`Skipping duplicate invoice with fsNumber ${invoice.fsNumber}`);
    //                 maxFsNo = Math.max(maxFsNo, invoice.fsNumber);
    //                 continue;
    //             }

    //             const lines = (invoice.lines || []).map(line => ({
    //                 lineIndex: line.lineIndex,
    //                 pluCode: line.pluCode,
    //                 itemName: line.itemName,
    //                 itemShortName: line.itemShortName,
    //                 itemDescription: line.itemDescription,
    //                 quantity: line.quantity,
    //                 unit_name: line.unit_name,
    //                 price: line.price,
    //                 lineDiscount: line.lineDiscount,
    //                 lineDiscountAmount: line.lineDiscountAmount,
    //                 lineDiscountType: line.lineDiscountType,
    //                 lineServiceCharge: line.lineServiceCharge,
    //                 lineServiceChargeAmount: line.lineServiceChargeAmount,
    //                 lineServiceChargeType: line.lineServiceChargeType,
    //                 date: this.convertDateFormat(line.date),
    //                 time: line.time,
    //                 lineTotal: line.lineTotal,
    //                 lineTotalTax: line.lineTotalTax,
    //                 lineTotalWithTax: line.lineTotalWithTax,
    //                 taxAmount: line.taxAmount,
    //                 taxRate: line.taxRate,
    //                 isVoided: line.isVoided,
    //             }));

    //             const invoiceVals = {
    //                 fsNumber: invoice.fsNumber,
    //                 referenceNumber: invoice.referenceNumber,
    //                 paymentType: invoice.paymentType,
    //                 paymentReferenceNumber: invoice.paymentReferenceNumber,
    //                 buyerName: invoice.buyerName,
    //                 buyerTradeName: invoice.buyerTradeName,
    //                 buyerTaxIdNumber: invoice.buyerTaxIdNumber,
    //                 buyerPhoneNumber: invoice.buyerPhoneNumber,
    //                 cashierName: invoice.cashierName,
    //                 headerMemo: invoice.headerMemo,
    //                 footerMemo: invoice.footerMemo,
    //                 checksum: invoice.timeStamp,
    //                 remark: invoice.remark,
    //                 approvedBy: invoice.approvedBy,
    //                 totalWithoutTax: invoice.totalWithoutTax,
    //                 totalTax: invoice.totalTax,
    //                 totalTaxabl1: invoice.totalTaxabl1,
    //                 totalTax1: invoice.totalTax1,
    //                 totalTaxabl2: invoice.totalTaxabl2,
    //                 totalTax2: invoice.totalTax2,
    //                 totalTaxabl3: invoice.totalTaxabl3,
    //                 totalTax3: invoice.totalTax3,
    //                 totalNonTax: invoice.totalNonTax,
    //                 totalWithTax: invoice.totalWithTax,
    //                 totalPaid: invoice.totalPaid,
    //                 totalDiscount: invoice.totalDiscount,
    //                 totalServiceCharge: invoice.totalServiceCharge,
    //                 total: invoice.total,
    //                 change: invoice.change,
    //                 zReportSent: invoice.zReportSent,
    //                 printed: invoice.printed,
    //                 date: this.convertDateFormat(invoice.date),
    //                 time: invoice.time,
    //                 qrCodeData: invoice.qrCodeData,
    //                 itemCount: invoice.itemCount,
    //                 zNo: invoice.zNo,
    //                 globalDiscountType: invoice.globalDiscountType,
    //                 globalDiscountAmount: invoice.globalDiscountAmount,
    //                 globalServiceChargeType: invoice.globalServiceChargeType,
    //                 globalServiceChargeAmount: invoice.globalServiceChargeAmount,
    //                 printCopy: invoice.printCopy,
    //                 ejPath: invoice.ejPath,
    //                 device_id: deviceId,
    //                 line_ids: lines.map(line => [0, 0, line]),
    //             };

    //             await this.orm.create("pos.invoice", [invoiceVals]);
    //             maxFsNo = Math.max(maxFsNo, invoice.fsNumber);
    //             syncedInvoices++;
    //         }
    //     }

    //     // --- Sync Refunds ---
    //     const [lastRefundId] = await this.orm.search(
    //         "pos.refund",
    //         [["device_id", "=", deviceId]],
    //         { order: "rfdNumber desc", limit: 1 }
    //     );
    //     if (lastRefundId) {
    //         const [lastRefund] = await this.orm.read("pos.refund", [lastRefundId], ["rfdNumber"]);
    //         maxRfdNo = lastRefund.rfdNumber || 0;
    //     }

    //     console.log(`Starting refund sync from rfdNumber ${maxRfdNo} for device ${device.mrc}`);

    //     while (true) {
    //         const result = window.Android.getRefundInvoicesAfterRfdNumber(
    //             JSON.stringify({ rfd_number: maxRfdNo }),
    //             device.mrc
    //         );

    //         let refunds;
    //         try {
    //             refunds = JSON.parse(result);
    //         } catch (e) {
    //             this.env.services.notification.add("Failed to parse refund invoice data from Android device.", {
    //                 type: "danger",
    //             });
    //             console.error(e);
    //             break;
    //         }

    //         if (!refunds || refunds.length === 0) break;

    //         for (const refund of refunds) {
    //             // Check for existing refund by rfdNumber
    //             const existingRefund = await this.orm.search(
    //                 "pos.refund",
    //                 [["rfdNumber", "=", refund.rfdNumber], ["device_id", "=", deviceId]],
    //                 { limit: 1 }
    //             );
    //             if (existingRefund.length > 0) {
    //                 console.log(`Skipping duplicate refund with rfdNumber ${refund.rfdNumber}`);
    //                 maxRfdNo = Math.max(maxRfdNo, refund.rfdNumber);
    //                 continue;
    //             }

    //             const lines = (refund.lines || []).map(line => ({
    //                 lineIndex: line.lineIndex,
    //                 itemName: line.itemName,
    //                 itemShortName: line.itemShortName,
    //                 itemDescription: line.itemDescription,
    //                 quantity: line.quantity,
    //                 unit_name: line.unit_name,
    //                 price: line.price,
    //                 lineDiscount: line.lineDiscount,
    //                 lineDiscountAmount: line.lineDiscountAmount,
    //                 lineDiscountType: line.lineDiscountType,
    //                 lineServiceCharge: line.lineServiceCharge,
    //                 lineServiceChargeAmount: line.lineServiceChargeAmount,
    //                 lineServiceChargeType: line.lineServiceChargeType,
    //                 lineTotal: line.lineTotal,
    //                 lineTotalTax: line.lineTotalTax,
    //                 lineTotalWithTax: line.lineTotalWithTax,
    //                 taxAmount: line.taxAmount,
    //                 taxRate: line.taxRate,
    //             }));

    //             const refundVals = {
    //                 rfdNumber: refund.rfdNumber,
    //                 referenceNumber: refund.referenceNumber,
    //                 paymentType: refund.paymentType,
    //                 paymentReferenceNumber: refund.paymentReferenceNumber,
    //                 buyerName: refund.buyerName,
    //                 buyerTradeName: refund.buyerTradeName,
    //                 buyerTaxIdNumber: refund.buyerTaxIdNumber,
    //                 buyerPhoneNumber: refund.buyerPhoneNumber,
    //                 cashierName: refund.cashierName,
    //                 headerMemo: refund.headerMemo,
    //                 footerMemo: refund.footerMemo,
    //                 checksum: refund.timeStamp,
    //                 remark: refund.remark,
    //                 approvedBy: refund.approvedBy,
    //                 totalWithoutTax: refund.totalWithoutTax,
    //                 totalTax: refund.totalTax,
    //                 totalTaxabl1: refund.totalTaxabl1,
    //                 totalTax1: refund.totalTax1,
    //                 totalTaxabl2: refund.totalTaxabl2,
    //                 totalTax2: refund.totalTax2,
    //                 totalTaxabl3: refund.totalTaxabl3,
    //                 totalTax3: refund.totalTax3,
    //                 totalNonTax: refund.totalNonTax,
    //                 totalWithTax: refund.totalWithTax,
    //                 totalPaid: refund.totalPaid,
    //                 totalDiscount: refund.totalDiscount,
    //                 totalServiceCharge: refund.totalServiceCharge,
    //                 total: refund.total,
    //                 change: refund.change,
    //                 zReportSent: refund.zReportSent,
    //                 printed: refund.printed,
    //                 date: this.convertDateFormat(refund.date),
    //                 time: refund.time,
    //                 qrCodeData: refund.qrCodeData,
    //                 itemCount: refund.itemCount,
    //                 zNo: refund.zNo,
    //                 globalDiscountType: refund.globalDiscountType,
    //                 globalDiscountAmount: refund.globalDiscountAmount,
    //                 globalServiceChargeType: refund.globalServiceChargeType,
    //                 globalServiceChargeAmount: refund.globalServiceChargeAmount,
    //                 commercialLogo: refund.commercialLogo,
    //                 printCopy: refund.printCopy,
    //                 ejPath: refund.ejPath,
    //                 device_id: deviceId,
    //                 line_ids: lines.map(line => [0, 0, line]),
    //             };

    //             await this.orm.create("pos.refund", [refundVals]);
    //             maxRfdNo = Math.max(maxRfdNo, refund.rfdNumber);
    //             syncedRefunds++;
    //         }
    //     }

    //     // --- Sync Z Reports ---
    //     const [lastZReportId] = await this.orm.search(
    //         "pos.zreport",
    //         [["device_id", "=", deviceId]],
    //         { order: "zNumber desc", limit: 1 }
    //     );
    //     if (lastZReportId) {
    //         const [lastZReport] = await this.orm.read("pos.zreport", [lastZReportId], ["zNumber"]);
    //         maxZNo = lastZReport.zNumber || 0;
    //     }

    //     console.log(`Starting Z report sync from zNumber ${maxZNo} for device ${device.mrc}`);

    //     while (true) {
    //         const result = window.Android.getZReportsAfterZNumber(
    //             JSON.stringify({ z_number: maxZNo }),
    //             device.mrc
    //         );

    //         let zReports;
    //         try {
    //             zReports = JSON.parse(result);
    //         } catch (e) {
    //             this.env.services.notification.add("Failed to parse Z report data from Android device.", {
    //                 type: "danger",
    //             });
    //             console.error(e);
    //             break;
    //         }

    //         if (!zReports || zReports.length === 0) break;

    //         for (const zReport of zReports) {
    //             // Check for existing Z Report by zNumber
    //             const existingZReport = await this.orm.search(
    //                 "pos.zreport",
    //                 [["zNumber", "=", zReport.zNumber], ["device_id", "=", deviceId]],
    //                 { limit: 1 }
    //             );
    //             if (existingZReport.length > 0) {
    //                 console.log(`Skipping duplicate Z report with zNumber ${zReport.zNumber}`);
    //                 maxZNo = Math.max(maxZNo, zReport.zNumber);
    //                 continue;
    //             }

    //             const zReportVals = {
    //                 zNumber: zReport.zNumber,
    //                 txbl1: zReport.txbl1,
    //                 txbl2: zReport.txbl2,
    //                 txbl3: zReport.txbl3,
    //                 notxbl: zReport.notxbl,
    //                 tax1: zReport.tax1,
    //                 tax1Val: zReport.tax1Val,
    //                 tax2: zReport.tax2,
    //                 tax2Val: zReport.tax2Val,
    //                 tax3: zReport.tax3,
    //                 tax3Val: zReport.tax3Val,
    //                 salesTotal: zReport.salesTotal,
    //                 txblTotal: zReport.txblTotal,
    //                 taxTotal: zReport.taxTotal,
    //                 rfdTxbl1: zReport.rfdTxbl1,
    //                 rfdTxbl2: zReport.rfdTxbl2,
    //                 rfdTxbl3: zReport.rfdTxbl3,
    //                 rfdNotxbl: zReport.rfdNotxbl,
    //                 rfdTax1: zReport.rfdTax1,
    //                 rfdTax2: zReport.rfdTax2,
    //                 rfdTax3: zReport.rfdTax3,
    //                 rfdSalesTotal: zReport.rfdSalesTotal,
    //                 rfdTxblTotal: zReport.rfdTxblTotal,
    //                 rfdTaxTotal: zReport.rfdTaxTotal,
    //                 accumulatedFs: zReport.accumulatedFs,
    //                 lastReceiptDate: zReport.lastReceiptDate && zReport.lastReceiptDate.trim() !== '' ? this.convertDateFormat(zReport.lastReceiptDate) : null,
    //                 lastReceiptTime: zReport.lastReceiptTime && zReport.lastReceiptTime.trim() !== '' ? zReport.lastReceiptTime : null,
    //                 lastFsNo: zReport.lastFsNo,
    //                 sessionFSCount: zReport.sessionFSCount,
    //                 accumulatedNfNo: zReport.accumulatedNfNo,
    //                 sessionNFCount: zReport.sessionNFCount,
    //                 accumulatedRfd: zReport.accumulatedRfd,
    //                 sessionRfdCount: zReport.sessionRfdCount,
    //                 sessionResetCount: zReport.sessionResetCount,
    //                 savedOnERCAFtp: zReport.savedOnERCAFtp,
    //                 date: this.convertDateFormat(zReport.date),
    //                 time: zReport.time,
    //                 checksum: zReport.timeStamp,
    //                 ejPath: zReport.ejPath,
    //                 isPrinted: zReport.isPrinted,
    //                 toBePrint: zReport.toBePrint,
    //                 device_id: deviceId,
    //             };

    //             await this.orm.create("pos.zreport", [zReportVals]);
    //             maxZNo = Math.max(maxZNo, zReport.zNumber);
    //             syncedZReports++;
    //         }
    //     }

    //     this.env.services.notification.add(
    //         `${syncedInvoices} invoices, ${syncedRefunds} refunds, and ${syncedZReports} Z reports synced successfully.`,
    //         { type: "success" }
    //     );
    // }
}

PosDeviceSync.template = "pos_device_sync.widget";

registry.category("view_widgets").add("pos_device_sync_component", {
    component: PosDeviceSync,
});