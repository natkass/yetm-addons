from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PosDevice(models.Model):
    _name = 'pos.device'
    _description = 'POS Device'

    mrc = fields.Char(string='MRC', required=True, index=True)
    name = fields.Char(string='Device Name', compute='_compute_name')
    invoice_ids = fields.One2many('pos.invoice', 'device_id', string='Invoices')
    refund_ids = fields.One2many('pos.refund', 'device_id', string='Refunds')
    zreport_ids = fields.One2many('pos.zreport', 'device_id', string='Z Reports')
    company_id = fields.Many2one(
            'res.company',
            string="Company",
            default=lambda self: self.env.company,
            required=True
        )
    @api.depends('mrc')
    def _compute_name(self):
        for device in self:
            device.name = device.mrc


    def action_sync(self):
        """Sync action for POS Device"""
        _logger.info(f"Sync action triggered for POS Device: {self.name}")
        return {
            'type': 'ir.actions.client',
            'tag': 'my_pos_device_sync',
            'params': {
                'title': 'Sync',
                'message': f'Sync triggered for device {self.name}',
                'type': 'info',
            }
        }

    @api.model
    def get_device_max_sync_values(self, device_id):
        """
        Get the maximum fsNumber, rfdNumber, and zNumber for a device
        using direct SQL queries to avoid issues with duplicates.
        """
        self.env.cr.execute("""
            SELECT COALESCE(MAX("fsNumber"), 0) as max_fs
            FROM pos_invoice
            WHERE device_id = %s
        """, (device_id,))
        max_fs = self.env.cr.fetchone()[0]
        
        self.env.cr.execute("""
            SELECT COALESCE(MAX("rfdNumber"), 0) as max_rfd
            FROM pos_refund
            WHERE device_id = %s
        """, (device_id,))
        max_rfd = self.env.cr.fetchone()[0]
        
        self.env.cr.execute("""
            SELECT COALESCE(MAX("zNumber"), 0) as max_z
            FROM pos_zreport
            WHERE device_id = %s
        """, (device_id,))
        max_z = self.env.cr.fetchone()[0]
        
        return {
            'max_fs_number': max_fs,
            'max_rfd_number': max_rfd,
            'max_z_number': max_z
        }