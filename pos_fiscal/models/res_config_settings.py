from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # POS Fiscal - Inventory Integration Settings
    pos_fiscal_enable_inventory = fields.Boolean(
        string='Enable POS Fiscal Inventory Integration',
        config_parameter='pos_fiscal.enable_inventory_integration',
        default=True,
        help='Enable automatic inventory updates for POS fiscal reconciliation'
    )
    pos_fiscal_create_picking_on_create = fields.Boolean(
        string='Create Picking for New Orders',
        config_parameter='pos_fiscal.create_picking_on_create',
        default=True,
        help='Automatically create stock pickings when creating orders from fiscal invoices'
    )
    pos_fiscal_create_picking_on_sync = fields.Boolean(
        string='Create Picking on Amount Sync',
        config_parameter='pos_fiscal.create_picking_on_sync',
        default=True,
        help='Create stock pickings when syncing orders with changed amounts'
    )
    pos_fiscal_validate_picking_auto = fields.Boolean(
        string='Auto-Validate Pickings',
        config_parameter='pos_fiscal.validate_picking_automatically',
        default=True,
        help='Automatically validate created stock pickings'
    )

    # POS Fiscal - Accounting Integration Settings
    pos_fiscal_enable_accounting = fields.Boolean(
        string='Enable POS Fiscal Accounting Integration',
        config_parameter='pos_fiscal.enable_accounting_integration',
        default=True,
        help='Enable automatic invoice creation and accounting updates'
    )
    pos_fiscal_auto_invoice_orders = fields.Boolean(
        string='Auto-Invoice Created Orders',
        config_parameter='pos_fiscal.auto_invoice_created_orders',
        default=True,
        help='Automatically create and post invoices for orders created from fiscal data'
    )
    pos_fiscal_auto_post_invoices = fields.Boolean(
        string='Auto-Post Invoices',
        config_parameter='pos_fiscal.auto_post_invoices',
        default=True,
        help='Automatically post created invoices'
    )
    pos_fiscal_auto_validate_payments = fields.Boolean(
        string='Auto-Validate Payments',
        config_parameter='pos_fiscal.auto_validate_payments',
        default=True,
        help='Automatically validate invoice payments'
    )

    # POS Fiscal - Reconciliation Settings
    pos_fiscal_auto_reconcile = fields.Boolean(
        string='Auto-Reconcile Orders',
        config_parameter='pos_fiscal.auto_reconcile_orders',
        default=False,
        help='Automatically reconcile orders when fiscal data is synced'
    )
    pos_fiscal_strict_matching = fields.Boolean(
        string='Strict Matching Mode',
        config_parameter='pos_fiscal.strict_matching_mode',
        default=True,
        help='Require exact amount matching during reconciliation'
    )
