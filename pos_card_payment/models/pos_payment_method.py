from odoo.exceptions import UserError
from odoo import fields, models, api, _

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('card', 'Card')]