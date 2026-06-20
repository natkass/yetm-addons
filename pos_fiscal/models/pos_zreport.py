from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class PosZReport(models.Model):
    _name = 'pos.zreport'
    _description = 'POS Z Report'

    zNumber = fields.Integer(string='Z Number', index=True)
    txbl1 = fields.Float(string='Taxable Amount 1')
    txbl2 = fields.Float(string='Taxable Amount 2')
    txbl3 = fields.Float(string='Taxable Amount 3')
    notxbl = fields.Float(string='Non-Taxable Amount')
    tax1 = fields.Float(string='Tax Rate 1')
    tax1Val = fields.Float(string='Tax Amount 1')
    tax2 = fields.Float(string='Tax Rate 2')
    tax2Val = fields.Float(string='Tax Amount 2')
    tax3 = fields.Float(string='Tax Rate 3')
    tax3Val = fields.Float(string='Tax Amount 3')
    salesTotal = fields.Float(string='Sales Total')
    txblTotal = fields.Float(string='Taxable Total')
    taxTotal = fields.Float(string='Tax Total')
    rfdTxbl1 = fields.Float(string='Refund Taxable Amount 1')
    rfdTxbl2 = fields.Float(string='Refund Taxable Amount 2')
    rfdTxbl3 = fields.Float(string='Refund Taxable Amount 3')
    rfdNotxbl = fields.Float(string='Refund Non-Taxable Amount')
    rfdTax1 = fields.Float(string='Refund Tax Rate 1')
    rfdTax2 = fields.Float(string='Refund Tax Rate 2')
    rfdTax3 = fields.Float(string='Refund Tax Rate 3')
    rfdSalesTotal = fields.Float(string='Refund Sales Total')
    rfdTxblTotal = fields.Float(string='Refund Taxable Total')
    rfdTaxTotal = fields.Float(string='Refund Tax Total')
    accumulatedFs = fields.Integer(string='Accumulated Fiscal Receipts')
    lastReceiptDate = fields.Date(string='Last Receipt Date')
    lastReceiptTime = fields.Char(string='Last Receipt Time')
    lastFsNo = fields.Integer(string='Last FS Number')
    sessionFSCount = fields.Integer(string='Session Fiscal Receipt Count')
    accumulatedNfNo = fields.Integer(string='Accumulated Non-Fiscal Receipts')
    sessionNFCount = fields.Integer(string='Session Non-Fiscal Receipt Count')
    accumulatedRfd = fields.Integer(string='Accumulated Refund Receipts')
    sessionRfdCount = fields.Integer(string='Session Refund Receipt Count')
    sessionResetCount = fields.Integer(string='Session Reset Count')
    savedOnERCAFtp = fields.Boolean(string='Saved on ERCA FTP')
    date = fields.Date(string='Date')
    time = fields.Char(string='Time')
    checksum = fields.Text(string='Checksum')
    ejPath = fields.Char(string='EJ Path')
    isPrinted = fields.Boolean(string='Printed')
    toBePrint = fields.Boolean(string='To Be Printed')
    device_id = fields.Many2one('pos.device', string='Device')
    
    _sql_constraints = [
        ('zNumber_device_id_unique', 'UNIQUE(zNumber, device_id)', 'Z Number must be unique per device.')
    ]