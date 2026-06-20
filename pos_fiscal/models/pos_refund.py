from odoo import models, fields, api

import logging

_logger = logging.getLogger(__name__)

class PosRefund(models.Model):
    _name = 'pos.refund'
    _description = 'POS Refund'
    _order = 'rfdNumber asc'

    rfdNumber = fields.Integer(string='Refund Number', index=True)
    referenceNumber = fields.Char(string='Reference Number')
    paymentType = fields.Char(string='Payment Type')
    paymentReferenceNumber = fields.Char(string='Payment Reference')
    buyerName = fields.Char(string='Buyer Name')
    buyerTradeName = fields.Char(string='Buyer Trade Name')
    buyerTaxIdNumber = fields.Char(string='Buyer Tax ID')
    buyerPhoneNumber = fields.Char(string='Buyer Phone Number')
    cashierName = fields.Char(string='Cashier Name')
    headerMemo = fields.Text(string='Header Memo')
    footerMemo = fields.Text(string='Footer Memo')
    checksum = fields.Text(string='Checksum')
    remark = fields.Text(string='Remark')
    approvedBy = fields.Char(string='Approved By')
    totalWithoutTax = fields.Float(string='Total Without Tax')
    totalTax = fields.Float(string='Total Tax')
    totalTaxabl1 = fields.Float(string='Taxable Amount 1')
    totalTax1 = fields.Float(string='Tax Amount 1')
    totalTaxabl2 = fields.Float(string='Taxable Amount 2')
    totalTax2 = fields.Float(string='Tax Amount 2')
    totalTaxabl3 = fields.Float(string='Taxable Amount 3')
    totalTax3 = fields.Float(string='Tax Amount 3')
    totalNonTax = fields.Float(string='Non-Taxable Total')
    totalWithTax = fields.Float(string='Total with Tax')
    totalPaid = fields.Float(string='Total Paid')
    totalDiscount = fields.Float(string='Total Discount')
    totalServiceCharge = fields.Float(string='Total Service Charge')
    total = fields.Float(string='Grand Total')
    change = fields.Float(string='Change')
    zReportSent = fields.Boolean(string='Z-Report Sent')
    printed = fields.Boolean(string='Printed')
    date = fields.Date(string='Date')
    time = fields.Char(string='Time')
    qrCodeData = fields.Text(string='QR Code Data')
    itemCount = fields.Integer(string='Item Count')
    zNo = fields.Integer(string='Invoice Number')
    globalDiscountType = fields.Char(string='Global Discount Type')
    globalDiscountAmount = fields.Float(string='Global Discount Amount')
    globalServiceChargeType = fields.Char(string='Global Service Charge Type')
    globalServiceChargeAmount = fields.Float(string='Global Service Charge Amount')
    commercialLogo = fields.Text(string='Commercial Logo')
    printCopy = fields.Integer(string='Print Copies')
    ejPath = fields.Char(string='EJ Path')
    device_id = fields.Many2one('pos.device', string='Device', ondelete='cascade')
    line_ids = fields.One2many('pos.refund.line', 'refund_id', string='Refund Lines')
    
    _sql_constraints = [
        ('rfdNumber_device_id_unique', 'UNIQUE(rfdNumber, device_id)', 'RFD Number must be unique per device.')
    ]


class PosRefundLine(models.Model):
    _name = 'pos.refund.line'
    _description = 'POS Refund Line'

    refund_id = fields.Many2one('pos.refund', string='Refund', ondelete='cascade')
    lineIndex = fields.Char(string='Line Index')
    itemName = fields.Char(string='Item Name')
    itemShortName = fields.Char(string='Item Short Name')
    itemDescription = fields.Text(string='Item Description')
    quantity = fields.Float(string='Quantity')
    unit_name = fields.Char(string='Unit Name')
    price = fields.Float(string='Unit Price')
    lineDiscount = fields.Float(string='Line Discount')
    lineDiscountAmount = fields.Float(string='Line Discount Amount')
    lineDiscountType = fields.Char(string='Line Discount Type')
    lineServiceCharge = fields.Float(string='Line Service Charge')
    lineServiceChargeAmount = fields.Float(string='Line Service Charge Amount')
    lineServiceChargeType = fields.Char(string='Line Service Charge Type')
    lineTotal = fields.Float(string='Line Total')
    lineTotalTax = fields.Float(string='Line Total Tax')
    lineTotalWithTax = fields.Float(string='Line Total with Tax')
    taxAmount = fields.Float(string='Tax Amount')
    taxRate = fields.Float(string='Tax Rate')