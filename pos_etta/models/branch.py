from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class BranchUser(models.Model):
    _name = 'branch.user'
    _description = 'Branch User'

    name = fields.Char(string="Branch Name")

class ResUsersInherit(models.Model):
    _inherit = 'res.users'

    branch = fields.Many2one("branch.user", string="Branch")

class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    branch = fields.Many2one("branch.user",string="Branch", required=True, default=lambda self: self._default_branch())

    @api.model
    def _default_branch(self):
        # Default branch based on the logged-in user's branch
        return self.env.user.branch

    @api.model
    def create(self, vals):
        # Validate if the user's branch is set
        if not self.env.user.branch:
            raise ValidationError("Your user account is not assigned to any branch. Please contact the administrator.")
        if not vals.get('branch'):
            vals['branch'] = self._default_branch().id
        return super(SaleOrderInherit, self).create(vals)

    def write(self, vals):
        # Optional: Add similar validation during update
        if 'branch' not in vals and not self.env.user.branch:
            raise ValidationError("Your user account is not assigned to any branch. Please contact the administrator.")
        return super(SaleOrderInherit, self).write(vals)