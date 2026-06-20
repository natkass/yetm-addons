from odoo import fields, models, _


class TransferRequestConfirmWizard(models.TransientModel):
    _name = 'transfer.request.confirm.wizard'
    _description = 'Transfer Request Confirmation Wizard'

    transfer_request_id = fields.Many2one(
        'transfer.request',
        string='Transfer Request',
        required=True,
    )
    message = fields.Text(string='Warning', readonly=True)
    action_type = fields.Selection([
        ('purchase_request', 'Purchase Request'),
        ('confirm', 'Confirm'),
        ('send_remaining', 'Send Remaining'),
    ], required=True)

    def action_proceed(self):
        self.ensure_one()
        rec = self.transfer_request_id
        if self.action_type == 'purchase_request':
            return rec.with_context(skip_warning=True).action_create_purchase_request()
        elif self.action_type == 'confirm':
            return rec.with_context(skip_warning=True).action_confirm()
        elif self.action_type == 'send_remaining':
            return rec.with_context(skip_warning=True).action_send_remaining()
