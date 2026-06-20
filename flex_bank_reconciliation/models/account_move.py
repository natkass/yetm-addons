# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_draft(self):
        # Check if any line has 'match' set to True
        for move in self:
            if any(line.is_reconciled for line in move.line_ids if line.is_reconciled == 'reconciled'):
                raise ValidationError(
                    _("You cannot set the document to 'Draft' when any line has a bank reconciliation."))

        return super(AccountMove, self).button_draft()



