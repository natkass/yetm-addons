from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PosDevice(models.Model):
    """POS Device with optional device-level configuration overrides"""
    _inherit = 'pos.device'

    # Device-specific overrides
    use_custom_config = fields.Boolean(
        string='Use Custom Configuration',
        default=False,
        help='Override global configuration for this specific device'
    )

    # Inventory Integration
    enable_inventory_integration = fields.Boolean(
        string='Enable Inventory Integration',
        default=True,
        help='Enable automatic inventory updates for this device'
    )
    create_picking_on_create = fields.Boolean(
        string='Create Picking for New Orders',
        default=True,
        help='Automatically create stock pickings when creating orders'
    )
    create_picking_on_sync = fields.Boolean(
        string='Create Picking on Sync',
        default=True,
        help='Create stock pickings when syncing orders'
    )

    # Accounting Integration
    enable_accounting_integration = fields.Boolean(
        string='Enable Accounting Integration',
        default=True,
        help='Enable automatic invoice creation for this device'
    )
    auto_invoice_created_orders = fields.Boolean(
        string='Auto-Invoice Created Orders',
        default=True,
        help='Automatically create and post invoices'
    )

    def get_reconciliation_config(self):
        """Get effective configuration for this device

        Returns device-specific config if enabled, otherwise returns global config
        """
        self.ensure_one()

        if self.use_custom_config:
            # Use device-specific configuration
            return {
                'auto_invoice_created': self.enable_accounting_integration and self.auto_invoice_created_orders,
                'create_inventory_picking': self.enable_inventory_integration and self.create_picking_on_create,
                'update_inventory_on_sync': self.enable_inventory_integration and self.create_picking_on_sync,
                'update_accounting_on_sync': False,
            }
        else:
            # Use global configuration from system parameters
            ICP = self.env['ir.config_parameter'].sudo()
            enable_inventory = ICP.get_param('pos_fiscal.enable_inventory_integration', default='True') == 'True'
            enable_accounting = ICP.get_param('pos_fiscal.enable_accounting_integration', default='True') == 'True'

            return {
                'auto_invoice_created': enable_accounting and ICP.get_param('pos_fiscal.auto_invoice_created_orders', default='True') == 'True',
                'create_inventory_picking': enable_inventory and ICP.get_param('pos_fiscal.create_picking_on_create', default='True') == 'True',
                'update_inventory_on_sync': enable_inventory and ICP.get_param('pos_fiscal.create_picking_on_sync', default='True') == 'True',
                'update_accounting_on_sync': False,  # Always false for safety
                'auto_post_invoices': enable_accounting and ICP.get_param('pos_fiscal.auto_post_invoices', default='True') == 'True',
                'auto_validate_payments': enable_accounting and ICP.get_param('pos_fiscal.auto_validate_payments', default='True') == 'True',
                'validate_picking_automatically': enable_inventory and ICP.get_param('pos_fiscal.validate_picking_automatically', default='True') == 'True',
            }
