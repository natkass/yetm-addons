from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.translate import _
from collections import defaultdict
from odoo.fields import datetime

class ManufacturingRequest(models.Model):
    _name = "manufacturing.request"
    _description = "Manufacturing Request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date desc"

    is_overdue = fields.Boolean(
        string="Overdue",
        compute='_compute_is_overdue',
        help="Request promise date has passed and it is still not delivered",
    )

    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_overdue = bool(
                rec.promise_date and
                rec.promise_date < now and
                rec.state != 'delivered'
            )

    # Existing fields ...

    create_month = fields.Integer(
        string="Month Created",
        compute="_compute_create_month_year",
        store=True
    )
    create_year = fields.Integer(
        string="Year Created",
        compute="_compute_create_month_year",
        store=True
    )

    @api.depends('create_date')
    def _compute_create_month_year(self):
        for rec in self:
            if rec.create_date:
                dt = fields.Datetime.from_string(rec.create_date)
                rec.create_month = dt.month
                rec.create_year = dt.year
            else:
                rec.create_month = 0
                rec.create_year = 0

    is_delayed = fields.Boolean(
        string="Delayed",
        compute="_compute_is_delayed",
        store=True
    )

    @api.depends('promise_date', 'state')
    def _compute_is_delayed(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_delayed = bool(
                rec.promise_date and
                rec.promise_date < now and
                rec.state not in ('delivered','cancelled')
            )

    def write(self, vals):
        res = super().write(vals)
        # check for new delays after write
        for rec in self:
            if rec.is_delayed and not rec.env.context.get('delay_notified'):
                rec.sudo()._notify_delay()
        return res

    def _notify_delay(self):
        group = self.env.ref("manufacturing_request.group_manufacturing_request_manager")
        for rec in self:
            
            message = (
                f"⚠️ Manufacturing Request {rec.name} "
                f"is delayed! Promise date was {rec.promise_date}."
            )
            rec.sudo().message_post(
                body=message,
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
                partner_ids=[p.id for p in group.users],
            )

    def _notify_delay(self):
        """Notify the manager group and schedule activities when delayed."""
        
        group = self.env.ref("manufacturing_request.group_manufacturing_request_manager")
        partners = group.users.mapped('partner_id')  # for group message
        
        for rec in self:
            message = (
                f"⚠️ Manufacturing Request {rec.name} is delayed! "
                f"Promise date was {rec.promise_date}."
            )
            
            #  Post notification to the whole group
            rec.sudo().message_post(
                body=message,
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
                partner_ids=partners.ids,
            )
            
            #  Schedule an activity for each manager individually
            for user in group.users:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',  # activity type
                    user_id=user.id,
                    summary="Manufacturing Request Delayed",
                    note=f"Request {rec.name} is delayed. Please review and take action.",
                    date_deadline=fields.Date.today(),  # optional: set deadline today
                )


    # Add tracking timestamps for each stage
    draft_date = fields.Datetime(string="Draft Date", default=fields.Datetime.now)
    submitted_date = fields.Datetime(string="Submitted Date")
    verified_date = fields.Datetime(string="Verified Date")
    manufactured_date = fields.Datetime(string="Manufactured Date")
    sent_date = fields.Datetime(string="Sent to Branch Date")
    delivered_date = fields.Datetime(string="Delivered Date")
    cancelled_date = fields.Datetime(string="Cancelled Date")

    avg_stage_hours = fields.Float(
        string="Average Stage Duration (hrs)",
        compute="_compute_avg_stage_duration",
        store=True
    )

    lead_time_hours = fields.Float(
        string="Lead Time (hrs)",
        compute="_compute_lead_time",
        store=True
    )

    
    @api.depends("create_date", "delivered_date")
    def _compute_lead_time(self):
        for rec in self:
            if rec.create_date and rec.delivered_date:
                delta = rec.delivered_date - rec.create_date
                rec.lead_time_hours = delta.total_seconds() / 3600
            else:
                rec.lead_time_hours = 0.0

        
    def get_stage_durations(self):
        self.ensure_one()

        # 1.  locate the 'state' field on the model once
        StateField = self.env['ir.model.fields'].search([
            ('model', '=', self._name),
            ('name', '=', 'state'),
        ], limit=1)

        # 2.  use field_id in the domain
        history = self.env['mail.tracking.value'].search([
            ('mail_message_id', 'in', self.message_ids.ids),
            ('field_id', '=', StateField.id),
        ], order='create_date asc')

        stages, prev = [], None
        for track in history:
            user_name = track.mail_message_id.author_id.name or track.mail_message_id.create_uid.name
            if prev:
                stages.append({
                    'stage': prev.old_value_char or str(prev.old_value_integer or ''),
                    'timestamp': prev.create_date,
                    'hours': round((track.create_date - prev.create_date).total_seconds() / 3600, 2),
                    'user': user_name,
                })
            prev = track

        # last stage
        if prev:
            stages.append({
                'stage': prev.new_value_char or str(prev.new_value_integer or ''),
                'timestamp': prev.create_date,
                'hours': 0.0,
                'user': user_name,
            })

        # fallback so the template never crashes
        if not stages:
            stages.append({
                'stage': self.state,
                'timestamp': self.create_date,
                'hours': 0.0,
                'user': self.create_uid.name,
            })

        return stages
    
    def get_background_color(self):
        """Return red color if delayed"""
        self.ensure_one()
        if self.promise_date and self.state != 'delivered' and self.promise_date < fields.Datetime.now():
            return '#f8d7da'
        return 'white'
    
    def action_print_lifecycle_request(self):
        return self.env.ref('manufacturing_request.action_report_lifecycle_request').report_action(self)
        

    def _compute_batch_kpis(self, requests):
        total_requests = len(requests)
        delayed_requests = sum(1 for r in requests if r.promise_date < fields.Datetime.now() and r.state != 'delivered')
        
        stage_hours = defaultdict(list)
        for r in requests:
            for d in r.get_stage_durations():
                stage_hours[d['stage']].append(d['hours'])

        avg_stage_hours = {stage: (sum(times)/len(times) if times else 0)
                        for stage, times in stage_hours.items()}

        return {
            'total_requests': total_requests,
            'delayed_requests': delayed_requests,
            'avg_stage_hours': avg_stage_hours
        }
    
    def action_print_lifecycle_batch(self):
        requests = self.env['manufacturing.request'].search([
            ('create_date','>=', self.date_from),
            ('create_date','<=', self.date_to),
            ('branch_id','=', self.branch_id.id) if self.branch_id else ()
        ])
        kpis = self._compute_batch_kpis(requests)
        return self.env.ref('manufacturing_request.report_lifecycle_batch').report_action(
            requests, data={'kpis': kpis}
        )

    
    
    @api.depends('draft_date','submitted_date','verified_date','manufactured_date','sent_date','delivered_date')
    def _compute_avg_stage_duration(self):
        for rec in self:
            durations = []
            if rec.draft_date and rec.submitted_date:
                durations.append((rec.submitted_date - rec.draft_date).total_seconds()/3600)
            if rec.submitted_date and rec.verified_date:
                durations.append((rec.verified_date - rec.submitted_date).total_seconds()/3600)
            if rec.verified_date and rec.manufactured_date:
                durations.append((rec.manufactured_date - rec.verified_date).total_seconds()/3600)
            if rec.manufactured_date and rec.sent_date:
                durations.append((rec.sent_date - rec.manufactured_date).total_seconds()/3600)
            if rec.sent_date and rec.delivered_date:
                durations.append((rec.delivered_date - rec.sent_date).total_seconds()/3600)
            rec.avg_stage_hours = sum(durations)/len(durations) if durations else 0

    name = fields.Char(
        string="Request Reference",
        required=True,
        copy=False,
        readonly=True,
        default="New"
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    responsible_id = fields.Many2one("res.users", string="Responsible", tracking=True, default=lambda self: self.env.user)
    partner_id = fields.Many2one("res.partner", string="Customer Name", required=True)    
    customer_phone = fields.Char(
        string="Customer Phone",
        related="sale_id.partner_id.phone",
        readonly=True
    )
    branch_id = fields.Many2one("res.branch", string="Requesting Branch", required=True)    
    promise_date = fields.Datetime(string="Promise Date", tracking=True, required=True)
    production_location_id = fields.Many2one(
        "stock.picking.type",
        string="Production Location",
        domain=[('code','=','mrp_operation')],
        tracking=True, required=True
    )
    sale_id = fields.Many2one("sale.order", string="Source Document", tracking=True)

    line_ids = fields.One2many("manufacturing.request.line", "request_id", string="Products", required=True)

    state = fields.Selection([
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("verified", "Verified"),
        ("manufactured", "Manufactured"),
        ("sent", "Sent to Branch"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ], string="Status", default="draft", tracking=True)

    request_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("verified", "Verified"),
            ("manufactured", "Manufactured"),
            ("sent", "Sent to Branch"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
        ],
        string="Request State",
        compute="_compute_request_state",
        store=True,
    )
    @api.depends('state')
    def _compute_request_state(self):
        for rec in self:
            rec.request_state = rec.state

    manufacturing_order_count = fields.Integer(
        string="Manufacturing Order",
        compute="_compute_manufacturing_order_count"
    )

    def _compute_manufacturing_order_count(self):
        for order in self:
            order.manufacturing_order_count = self.env["mrp.production"].search_count([
                ("origin", "=", order.name)
            ])

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            vals["name"] = self.env["ir.sequence"].next_by_code("manufacturing.request") or "New"
        return super().create(vals)

    def action_submit(self):
        self.write({"state": "submitted", "submitted_date": fields.Datetime.now()})

    def action_verify(self):
        self.write({"state": "verified", "verified_date": fields.Datetime.now()})


    def action_manufacture(self):
        """Create and confirm Manufacturing Orders from request lines"""
        MrpProduction = self.env["mrp.production"]

        self.write({"state": "manufactured", "manufactured_date": fields.Datetime.now()})

        for request in self:
            for line in request.line_ids:
                if not line.product_id:
                    continue

                # Find BOM (either from line or lookup)
                bom = self.env["mrp.bom"].search([
                    ("product_tmpl_id", "=", line.product_id.product_tmpl_id.id),
                    ("company_id", "in", [line.env.company.id, False]),
                    ("type", "=", "normal"),
                ], limit=1)

                if not bom:
                    raise UserError(
                        _("No Bill of Materials found for product %s.") 
                        % line.product_id.display_name
                    )

                # Create the Manufacturing Order
                mo = MrpProduction.create({
                    "product_id": line.product_id.id,
                    "product_qty": line.product_uom_qty,
                    "product_uom_id": line.product_id.uom_id.id,
                    "bom_id": bom.id,
                    "origin": request.name,  # source document = request name
                    "company_id": request.company_id.id,
                    "date_start": fields.Datetime.now(),  # today’s datetime
                    "picking_type_id": request.production_location_id.id,
                })

                # Confirm and plan MO
                mo.action_confirm()
                mo.button_mark_done()

            

    def action_sent(self):
        self.write({"state": "sent", "sent_date": fields.Datetime.now()})

    def action_deliver(self):
        self.write({"state": "delivered", "delivered_date": fields.Datetime.now()})

    def action_cancel(self):
        self.write({"state": "cancelled", "cancelled_date": fields.Datetime.now()})

    def action_reset_draft(self):
        self.write({"state": "draft"})

    def action_view_manufacturing_order(self):
        self.ensure_one()
        return {
            "name": "Manufacturing Orders",
            "type": "ir.actions.act_window",
            "res_model": "mrp.production",
            "view_mode": "tree,form",
            "domain": [("origin", "=", self.name)],
            "context": {"default_sale_id": self.id},
        }
    
    def action_print_request(self):
        return self.env.ref(
            "manufacturing_request.action_report_manufacturing_request"
        ).report_action(self)



class ManufacturingRequestLine(models.Model):
    _name = "manufacturing.request.line"
    _description = "Manufacturing Request Line"

    request_id = fields.Many2one("manufacturing.request", string="Request", ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Product", required=True)
    product_uom_qty = fields.Float(string="Quantity", required=True)
    
    product_uom = fields.Many2one("uom.uom",string="Unit of Measure",related="product_id.uom_id",store=True,readonly=True,)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id')
    bom_id = fields.Many2one(
        "mrp.bom",
        string="Bill of Materials",
        compute="_compute_bom_id",
        store=True,
        readonly=True,
    )
    remark = fields.Char(string="Remark", tracking=True)

    @api.depends("product_id")
    def _compute_bom_id(self):
        for line in self:
            if not line.product_id:
                line.bom_id = False
                continue
            
            bom = self.env["mrp.bom"].search([
                ("product_tmpl_id", "=", line.product_id.product_tmpl_id.id),
                ("company_id", "in", [line.env.company.id, False]),
                ("type", "=", "normal"),
            ], limit=1)

            line.bom_id = bom.id if bom else False

    
