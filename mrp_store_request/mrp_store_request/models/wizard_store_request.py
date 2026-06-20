from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpStoreRequestWizard(models.TransientModel):
    _name = 'mrp.store.request.wizard'
    _description = 'Create Store Request Wizard'

    mrp_production_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order',
        required=True,
        readonly=True,
    )
    finished_product_id = fields.Many2one(
        'product.product',
        string='Finished Product',
        related='mrp_production_id.product_id',
        readonly=True,
    )
    line_ids = fields.One2many(
        'mrp.store.request.wizard.line',
        'wizard_id',
        string='Lines',
    )
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Operation Type',
    )

    @api.onchange('picking_type_id')
    def _onchange_picking_type_id(self):
        for line in self.line_ids:
            line.picking_type_id = self.picking_type_id

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        mo_id = self.env.context.get('default_mrp_production_id')
        if mo_id:
            mo = self.env['mrp.production'].browse(mo_id)

            # Find products already covered by existing store requests for this MO
            existing_requests = self.env['transfer.request'].search([
                ('mrp_production_id', '=', mo.id),
            ])
            already_requested_product_ids = set(
                item.product_id.id
                for req in existing_requests
                for item in req.item_ids
                if item.product_id
            )

            finished_name = mo.product_id.display_name if mo.product_id else ''
            lines = []

            # Component rows
            for move in mo.move_raw_ids:
                if not move.product_id or move.product_uom_qty <= 0:
                    continue
                if move.product_id.id in already_requested_product_ids:
                    continue
                lines.append((0, 0, {
                    'line_type': 'component',
                    'product_id': move.product_id.id,
                    'qty': move.product_uom_qty,
                    'uom_id': move.product_uom.id,
                    'finished_product_name': finished_name,
                }))

            # Finished product row
            if mo.product_id and mo.product_id.id not in already_requested_product_ids:
                lines.append((0, 0, {
                    'line_type': 'finished',
                    'product_id': mo.product_id.id,
                    'qty': mo.product_qty,
                    'uom_id': mo.product_uom_id.id,
                    'finished_product_name': finished_name,
                }))

            if not lines:
                raise UserError(_("All products already have store requests created for this manufacturing order."))

            res['line_ids'] = lines
        return res

    def action_create_requests(self):
        self.ensure_one()

        if not self.line_ids:
            raise UserError(_("No lines to create requests from."))

        lines_with_op = self.line_ids.filtered(lambda l: l.picking_type_id)
        if not lines_with_op:
            raise UserError(_("Please assign an operation type to at least one line."))

        # Group lines by operation type
        groups = {}
        for line in lines_with_op:
            op_id = line.picking_type_id.id
            if op_id not in groups:
                groups[op_id] = []
            groups[op_id].append(line)

        created_requests = self.env['transfer.request']

        for op_id, lines in groups.items():
            op_type = self.env['stock.picking.type'].browse(op_id)
            src_location = op_type.default_location_src_id
            dest_location = op_type.default_location_dest_id

            if not src_location or not dest_location:
                raise UserError(_(
                    "Operation type '%s' has no default source or destination location configured."
                ) % op_type.display_name)

            request = self.env['transfer.request'].create({
                'picking_type_id': op_type.id,
                'location_id': src_location.id,
                'location_dest_id': dest_location.id,
                'mrp_production_id': self.mrp_production_id.id,
            })

            for line in lines:
                self.env['transfer.request.item'].create({
                    'transfer_request_id': request.id,
                    'product_id': line.product_id.id,
                    'demand': line.qty,
                })

            created_requests |= request

        return {
            'type': 'ir.actions.act_window',
            'name': _('Store Requests'),
            'res_model': 'transfer.request',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_requests.ids)],
        }


class MrpStoreRequestWizardLine(models.TransientModel):
    _name = 'mrp.store.request.wizard.line'
    _description = 'Store Request Wizard Line'

    wizard_id = fields.Many2one(
        'mrp.store.request.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    line_type = fields.Selection([
        ('component', 'Component'),
        ('finished', 'Finished Product'),
    ], string='Type', default='component')
    product_id = fields.Many2one(
        'product.product',
        string='Product',
    )
    finished_product_name = fields.Char(
        string='Finished Product',
    )
    component_display = fields.Html(
        string='Component / Finished Product',
        compute='_compute_component_display',
        sanitize=False,
    )
    qty = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
    )
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Operation Type',
    )

    @api.depends('product_id', 'finished_product_name', 'line_type')
    def _compute_component_display(self):
        for line in self:
            if not line.product_id:
                line.component_display = ''
            elif line.line_type == 'finished':
                line.component_display = (
                    '<div style="line-height:1.4">'
                    '<small class="text-muted">Finished Product</small><br/>'
                    '<span><strong>%s</strong></span>'
                    '</div>'
                ) % line.product_id.display_name
            elif line.finished_product_name:
                line.component_display = (
                    '<div style="line-height:1.4">'
                    '<span>%s</span><br/>'
                    '<small class="text-muted">&#8594; %s</small>'
                    '</div>'
                ) % (line.product_id.display_name, line.finished_product_name)
            else:
                line.component_display = '<span>%s</span>' % line.product_id.display_name
