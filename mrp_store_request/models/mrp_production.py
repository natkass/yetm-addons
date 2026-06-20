from odoo import api, fields, models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    store_request_ids = fields.One2many(
        'transfer.request', 'mrp_production_id',
        string='Store Requests',
    )
    store_request_count = fields.Integer(
        string='Store Requests',
        compute='_compute_store_request_count',
    )

    @api.depends('store_request_ids')
    def _compute_store_request_count(self):
        for rec in self:
            rec.store_request_count = len(rec.store_request_ids)

    def action_open_store_request_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Store Request'),
            'res_model': 'mrp.store.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_mrp_production_id': self.id,
            },
        }

    def action_view_store_requests(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Store Requests'),
            'res_model': 'transfer.request',
            'view_mode': 'list,form',
            'domain': [('mrp_production_id', '=', self.id)],
        }
        if self.store_request_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.store_request_ids[0].id
        return action
