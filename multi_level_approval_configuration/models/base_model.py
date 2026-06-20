##############################################################################
#
#    Copyright Domiup (<http://domiup.com>).
#
##############################################################################

from odoo import models


class BaseModel(models.AbstractModel):
    _inherit = "base"

    def write(self, vals):
        self.env["multi.approval.type"].check_rule(self, vals)
        res = super().write(vals)
        return res
