from datetime import date
from odoo import api, fields, models, _
from collections import defaultdict
from dateutil.relativedelta import relativedelta


class TargetAchieve(models.Model):
    _name = 'target.achieve'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Franchisee Target vs Achievement'

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirm", "Confirmed"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    selected_date = fields.Date(
        string="Reference Date",
        default=lambda self: date.today()
    )

    name = fields.Char(
        string='Name',
        compute='_compute_order_and_achieved',
        store=True,
        help="Auto created name which is a combination of Franchisee and timespan."
    )

    franchisee_id = fields.Many2one(
        'res.partner',
        string="Franchisee",
        required=True,
        tracking=True,
        domain=lambda self: self._get_franchisee_domain(),
        help="Customer (Franchisee) assigned under a locked Account Manager record."
    )

    acc_man_id = fields.Many2one(
        'hr.employee',
        compute='_compute_acc_man_id',
        string="Account Manager",
        store=True,
        help="Account Manager responsible for the selected Franchisee."
    )

    
    franchisee_target = fields.Float(
        'Franchisee Target',
        required=True,
        tracking=True,
        help="Value for the Franchisee target to reach.",
        compute="_compute_franchisee_target",
        default=0.0,
        copy=False,
        
    )

    
    time_span = fields.Selection(
        [('daily', 'Daily'),
         ('monthly', 'Monthly'),
         ('yearly', 'Yearly')],
        string='Time Span',
        default='monthly',
        required=True,
        tracking=True,
    )

    date_from = fields.Date(
        string="From Date",
        compute="_compute_date_range_and_label",
        store=True
    )
    date_to = fields.Date(
        string="To Date",
        compute="_compute_date_range_and_label",
        store=True
    )

    time_span_label = fields.Char(
        string="Selected Period",
        compute="_compute_date_range_and_label",
        store=False
    )

    sale_order_count = fields.Integer(compute="_compute_order_and_achieved", string="Manual Orders", store=True)
    pos_order_count = fields.Integer(compute="_compute_order_and_achieved", string="PoS Orders", store=True)
    franchisee_order_count = fields.Integer(
        string="Franchisee Orders",
        compute="_compute_order_and_achieved",
        store=True,
    )

    sale_achieved_amt = fields.Float(compute="_compute_order_and_achieved", store=True)
    pos_achieved_amt = fields.Float(compute="_compute_order_and_achieved", store=True)
    franchisee_achieved_amt = fields.Float(
        string='Franchisee Achieved Amount',
        compute="_compute_order_and_achieved",
        store=True,
        compute_sudo=True
    )

    franchisee_achieved_percent = fields.Float(
        string="Achieved %",
        compute="_compute_franchisee_achieved_percent",
        store=True,
    )

    
    product_summary_ids = fields.One2many(
        "target.achieve.product",
        "target_id",
        string="Products Summary",
        compute="_compute_order_and_achieved",
        store=True,
    )

    acc_man_manager_id = fields.Many2one(
        "target.achieve.manager",
        string="Account Manager Target",
        help="Link back to the Account Manager target period this belongs to.",
    )

    line_ids = fields.One2many("target.achieve.line", "target_id", string="Lines")

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    _sql_constraints = [
        ('unique_combination', 'unique (name)',
         "Similar Target for the same franchisee already exists."),
        ('check_franchisee_target',
         'CHECK(franchisee_target > 0.0)',
         "The Franchisee Target cannot be zero.",),
    ]

    # -------------------------------
    # COMPUTES
    # -------------------------------

    def action_recompute(self):
        """Manual recompute triggered by user."""
        self._compute_order_and_achieved()
        # refresh the lines (optional)
        self.line_ids._compute_achieved()

    def action_confirm(self):
        
        for rec in self:
            rec.state = "confirm"

    def action_cancel(self):
        
        for rec in self:
            rec.state = "cancel"

    @api.depends("line_ids.product_summary_ids")
    def _compute_product_summary(self):
        for rec in self:
            summary_data = {}
            for line in rec.line_ids:
                for ps in line.product_summary_ids:
                    key = ps.product_id.id
                    if key not in summary_data:
                        summary_data[key] = {
                            "product_id": ps.product_id.id,
                            "qty": 0.0,
                            "amount": 0.0,
                        }
                    summary_data[key]["qty"] += ps.total_qty
                    summary_data[key]["amount"] += ps.total_amount

            # reset and rebuild the summary
            rec.product_summary_ids = [(5, 0, 0)]  # clear
            rec.product_summary_ids = [(0, 0, vals) for vals in summary_data.values()]

    @api.depends("line_ids.target_amount")
    def _compute_franchisee_target(self):
        for rec in self:
            rec.franchisee_target = sum(rec.line_ids.mapped("target_amount"))

    @api.depends('franchisee_id')
    def _compute_acc_man_id(self):
        for rec in self:
            rec.acc_man_id = False
            if rec.franchisee_id:
                amc = self.env['account.manager.customer'].search([
                    ('state', '=', 'locked'),
                    ('customer_ids', 'in', rec.franchisee_id.id)
                ], limit=1)
                if amc:
                    rec.acc_man_id = amc.account_man_id

    @api.model
    def _get_franchisee_domain(self):
        amc_locked = self.env['account.manager.customer'].search([('state', '=', 'locked')])
        locked_customers = amc_locked.mapped('customer_ids')
        return [('id', 'in', list(set(locked_customers.ids)))]

    @api.depends("time_span")
    def _compute_date_range_and_label(self):
        
        for rec in self:
            today = rec.selected_date or date.today()
            if rec.time_span == "daily":
                rec.date_from = today
                rec.date_to = today
                rec.time_span_label = today.strftime("%A, %d %B %Y")
            elif rec.time_span == "monthly":
                rec.date_from = today.replace(day=1)
                next_month = today.replace(day=28) + relativedelta(days=4)
                rec.date_to = next_month - relativedelta(days=next_month.day)
                rec.time_span_label = today.strftime("%B %Y")
            elif rec.time_span == "yearly":
                rec.date_from = today.replace(month=1, day=1)
                rec.date_to = today.replace(month=12, day=31)
                rec.time_span_label = today.strftime("%Y")
            else:
                rec.date_from = rec.date_to = False
                rec.time_span_label = ""

    


    
    @api.depends("line_ids.target_amount","line_ids.achieved_amount" )
    def _compute_franchisee_achieved_percent(self):
        for rec in self:
            target = sum(rec.line_ids.mapped("target_amount"))
            achieved = sum(rec.line_ids.mapped("achieved_amount"))
            rec.franchisee_achieved_percent = (
                (achieved / target) * 100
                if target > 0 else 0
            )
    

    @api.depends(
        'franchisee_id',
        'time_span',
        'date_from',
        'date_to',
        'selected_date',
        'franchisee_id.sale_order_ids.x_studio_manually_sold',
        'franchisee_id.sale_order_ids.state',
        'franchisee_id.sale_order_ids.date_order',
        'franchisee_id.sale_order_ids.order_line.price_subtotal',
        'franchisee_id.sale_order_ids.order_line.product_uom_qty',
        'franchisee_id.pos_order_ids.state',
        'franchisee_id.pos_order_ids.date_order',
        'franchisee_id.pos_order_ids.lines.price_subtotal',
        'franchisee_id.pos_order_ids.lines.qty',
        
    )
    def _compute_order_and_achieved(self):
        for rec in self:

            sale_count = pos_count = 0
            sale_achieved = pos_achieved = 0.0

            product_totals = defaultdict(lambda: {"qty": 0.0, "amount": 0.0})
            
            rec.name = f"{rec.franchisee_id.name}:{rec.time_span_label}"

            if rec.franchisee_id:

                # ---- SALE ORDERS ----
                sale_domain = [
                    ('state', 'in', ['sale', 'done']),
                    ('partner_id', '=', rec.franchisee_id.id),
                    ('x_studio_manually_sold', '=', True),
                ]

                if rec.date_from:
                    sale_domain.append(('date_order', '>=', rec.date_from))
                if rec.date_to:
                    sale_domain.append(('date_order', '<=', rec.date_to))

                sale_orders = self.env['sale.order'].search(sale_domain)

                sale_count = len(sale_orders)

                for so in sale_orders:
                    for line in so.order_line:
                        sale_achieved += line.price_subtotal
                        product_totals[line.product_id.id]["qty"] += line.product_uom_qty
                        product_totals[line.product_id.id]["amount"] += line.price_subtotal

                # ---- POS ORDERS ----
                pos_domain = [
                    ('state', 'in', ['paid', 'invoiced', 'done']),
                    ('partner_id', '=', rec.franchisee_id.id),
                ]

                if rec.date_from:
                    pos_domain.append(('date_order', '>=', rec.date_from))
                if rec.date_to:
                    pos_domain.append(('date_order', '<=', rec.date_to))

                pos_orders = self.env['pos.order'].search(pos_domain)

                pos_count = len(pos_orders)

                for po in pos_orders:
                    for line in po.lines:
                        pos_achieved += line.price_subtotal
                        product_totals[line.product_id.id]["qty"] += line.qty
                        product_totals[line.product_id.id]["amount"] += line.price_subtotal

            # ---- Assign counters ----
            rec.sale_order_count = sale_count
            rec.pos_order_count = pos_count
            rec.franchisee_order_count = sale_count + pos_count

            # ---- Assign achieved amounts ----
            rec.sale_achieved_amt = sale_achieved
            rec.pos_achieved_amt = pos_achieved
            rec.franchisee_achieved_amt = sale_achieved + pos_achieved

            # ---- Rebuild product summary ----
            rec.product_summary_ids = [(5, 0, 0)] + [
                (0, 0, {
                    "product_id": product_id,
                    "total_qty": totals["qty"],
                    "total_amount": totals["amount"],
                })
                for product_id, totals in product_totals.items()
            ]


    @api.depends('franchisee_id', 'time_span', 'time_span_label')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.franchisee_id.name}:{record.time_span_label}"

    def action_view_franchisee_orders(self):
        """Open sales orders related to this franchisee and time span"""
        self.ensure_one()

        if not self.date_from or not self.date_to:
            # fallback to today if dates are missing
            ref_date = self.selected_date or fields.Date.today()
            date_from = ref_date
            date_to = ref_date
        else:
            date_from = self.date_from
            date_to = self.date_to

        domain = [
            ('state', '=', 'sale'),
            ('date_order', '>=', date_from),
            ('date_order', '<=', date_to),
            ('x_studio_manually_sold', '=', True),
        ]

        if self.franchisee_id:
            domain.append(('partner_id', '=', self.franchisee_id.id))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Franchisee Sales Orders'),
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {'create': False},
        }

        
    def action_view_franchisee_pos_orders(self):
        """Open POS orders related to this franchisee and time span"""
        self.ensure_one()

        # Safety fallback if date_from/date_to are missing
        if not self.date_from or not self.date_to:
            ref_date = self.selected_date or fields.Date.today()
            date_from = ref_date
            date_to = ref_date
        else:
            date_from = self.date_from
            date_to = self.date_to

        domain = [
            ('state', 'in', ['paid', 'invoiced', 'done']),
            ('date_order', '>=', date_from),
            ('date_order', '<=', date_to),
            
        ]

        if self.franchisee_id:
            domain.append(('partner_id', '=', self.franchisee_id.id))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Franchisee POS Orders'),
            'res_model': 'pos.order',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {'create': False},
        }

class TargetAchieveLine(models.Model):
    _name = "target.achieve.line"
    _description = "Franchisee Target Line by Category"

    

    target_id = fields.Many2one(
        "target.achieve",
        string="Franchisee Target",
        ondelete="cascade",
        required=True,
    )

    

    # Inherit time span and dates from parent
    time_span = fields.Selection(
        related="target_id.time_span", 
        store=True,
        readonly=True,
    )
    date_from = fields.Date(
        related="target_id.date_from",
        store=True,
        readonly=True,
    )
    date_to = fields.Date(
        related="target_id.date_to",
        store=True,
        readonly=True,
    )

    category_id = fields.Many2one(
        "franchise.product.category",
        string="Product Category",
        required=True,
        tracking=True,
    )

    target_amount = fields.Float(
        string="Target Amount",
        required=True,
        tracking=True,
    )

    achieved_amount = fields.Float(
        string="Achieved Amount",
        compute="_compute_achieved",
        store=True,
    )

    achieved_percent = fields.Float(
        string="Achieved %",
        compute="_compute_achieved",
        store=True,
    )

    product_summary_ids = fields.One2many(
        "target.achieve.product",
        "target_line_id",
        string="Products Summary",
        compute="_compute_achieved",
        store=True,
    )

    currency_id = fields.Many2one(
        related="target_id.currency_id",
        string="Currency",
        store=True,
        readonly=True,
    )

    # @api.depends("target_id", "category_id")
    @api.depends(
        'target_amount',
        'target_id.franchisee_id',
        'target_id.time_span',
        'target_id.date_from',
        'target_id.date_to',
        'target_id.selected_date',
        'target_id.franchisee_id.sale_order_ids.x_studio_manually_sold',
        'target_id.franchisee_id.sale_order_ids.state',
        'target_id.franchisee_id.sale_order_ids.date_order',
        'target_id.franchisee_id.sale_order_ids.order_line.price_subtotal',
        'target_id.franchisee_id.sale_order_ids.order_line.product_uom_qty',
        'target_id.franchisee_id.pos_order_ids.state',
        'target_id.franchisee_id.pos_order_ids.date_order',
        'target_id.franchisee_id.pos_order_ids.lines.price_subtotal',
        'target_id.franchisee_id.pos_order_ids.lines.qty',
        
    )
    def _compute_achieved(self):
        for line in self:
            total_amount = 0.0
            product_totals = defaultdict(lambda: {"qty": 0.0, "amount": 0.0})

            franchisee = line.target_id.franchisee_id
            date_from = line.target_id.date_from
            date_to = line.target_id.date_to

            if franchisee and line.category_id:
                # --- Sale Orders ---
                sale_orders = line.env['sale.order'].search([
                    ('partner_id', '=', franchisee.id),
                    ('state', 'in', ['sale', 'done']),
                    ('date_order', '>=', date_from),
                    ('date_order', '<=', date_to),
                    ('x_studio_manually_sold', '=', True)
                ])
                for so in sale_orders:
                    for l in so.order_line:
                        if line.category_id.product_tag_id and set(l.product_id.product_tag_ids.ids) & set(line.category_id.product_tag_id.ids):
                            total_amount += l.price_subtotal
                            product_totals[l.product_id.id]["qty"] += l.product_uom_qty
                            product_totals[l.product_id.id]["amount"] += l.price_subtotal

                # --- POS Orders ---
                pos_orders = line.env['pos.order'].search([
                    ('partner_id', '=', franchisee.id),
                    ('state', 'in', ['paid', 'done', 'invoiced']),
                    ('date_order', '>=', date_from),
                    ('date_order', '<=', date_to),
                ])
                for po in pos_orders:
                    for l in po.lines:
                        if line.category_id.product_tag_id and set(l.product_id.product_tag_ids.ids) & set(line.category_id.product_tag_id.ids):
                            total_amount += l.price_subtotal
                            product_totals[l.product_id.id]["qty"] += l.qty
                            product_totals[l.product_id.id]["amount"] += l.price_subtotal

            line.achieved_amount = total_amount
            line.achieved_percent = (total_amount / line.target_amount * 100) if line.target_amount else 0.0

            # Reset and rebuild product summary
            line.product_summary_ids = [(5, 0, 0)] + [
                (0, 0, {
                    "product_id": pid,
                    "total_qty": vals["qty"],
                    "total_amount": vals["amount"]
                }) for pid, vals in product_totals.items()
            ]

class TargetAchieveProduct(models.Model):
    _name = "target.achieve.product"
    _description = "Target Achieve Product Summary"

    target_id = fields.Many2one("target.achieve", string="Target", ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    total_qty = fields.Float(string="Total Quantity", readonly=True)
    total_amount = fields.Monetary(string="Total Amount", currency_field="currency_id", readonly=True)
    currency_id = fields.Many2one(related="target_id.currency_id", store=True, readonly=True)
    target_line_id = fields.Many2one(
        "target.achieve.line",
        string="Target Line",
        ondelete="cascade",
    )


class TargetAchieveManager(models.Model):
    _name = "target.achieve.manager"
    _description = "Target vs Achievement (Account Manager Level)"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        help="Auto created name which is a combination of Account Manager and timespan."
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirm", "Confirmed"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    acc_man_id = fields.Many2one("hr.employee", string="Account Manager", required=True, tracking=True)

    time_span = fields.Selection(
        [('daily', 'Daily'),
         ('monthly', 'Monthly'),
         ('yearly', 'Yearly')],
        string='Time Span',
        default='monthly',
        required=True,
        tracking=True,
    )

    selected_date = fields.Date(
        string="Reference Date",
        default=lambda self: date.today()
    )

    date_from = fields.Date(
        string="From Date",
        compute="_compute_date_range_and_label",
        store=True
    )
    date_to = fields.Date(
        string="To Date",
        compute="_compute_date_range_and_label",
        store=True
    )

    target_record_ids = fields.Many2many(
        "target.achieve",
        string="Target Records",
        compute="_compute_acc_man_totals",
        store=False,
    )

    acc_man_target = fields.Float(string="Total Target", compute="_compute_acc_man_totals")
    acc_man_achieved_amt = fields.Float(string="Total Achieved", compute="_compute_acc_man_totals")
    acc_man_achieved_percent = fields.Float(string="Achieved %", compute="_compute_acc_man_totals")

    franchisee_target_ids = fields.One2many(
        "target.achieve", "acc_man_id", string="Franchisee Targets"
    )

    manager_target_count = fields.Integer(
        string="Manager Targets",
        compute="_compute_acc_man_totals",
        store=True,
    )

    time_span_label = fields.Char(
        string="Selected Period",
        compute="_compute_date_range_and_label",
        store=False
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    _sql_constraints = [
        ('unique_accman_period',
        'unique(acc_man_id, time_span, date_from, date_to)',
        "A target for this Account Manager and period already exists."),
    ]

    @api.depends('acc_man_id', 'time_span', 'time_span_label')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.acc_man_id.name}:{record.time_span_label}"

    def action_confirm(self):
        
        for rec in self:
            rec.state = "confirm"

    def action_cancel(self):
        
        for rec in self:
            rec.state = "cancel"

    @api.depends("time_span", "selected_date")
    def _compute_date_range_and_label(self):
        
        for rec in self:
            today = rec.selected_date or date.today()
            if rec.time_span == "daily":
                rec.date_from = today
                rec.date_to = today
                rec.time_span_label = today.strftime("%A, %d %B %Y")
            elif rec.time_span == "monthly":
                rec.date_from = today.replace(day=1)
                next_month = today.replace(day=28) + relativedelta(days=4)
                rec.date_to = next_month - relativedelta(days=next_month.day)
                rec.time_span_label = today.strftime("%B %Y")
            elif rec.time_span == "yearly":
                rec.date_from = today.replace(month=1, day=1)
                rec.date_to = today.replace(month=12, day=31)
                rec.time_span_label = today.strftime("%Y")
            else:
                rec.date_from = rec.date_to = False
                rec.time_span_label = ""

    @api.depends(
        'acc_man_id',
        'time_span',
        'date_from',
        'date_to',
        'franchisee_target_ids',
        'franchisee_target_ids.franchisee_target',
        'franchisee_target_ids.franchisee_achieved_amt',
    )
    def _compute_acc_man_totals(self):
        for rec in self:
            total_target = 0.0
            total_achieved = 0.0
            target_count = 0
            target_records = self.env['target.achieve']

            if rec.acc_man_id:
                
                domain = [
                    ('acc_man_id', '=', rec.acc_man_id.id),
                    ('date_from', '>=', rec.date_from),
                    ('date_to', '<=', rec.date_to),
                    
                ]

                if rec.time_span:
                    domain.append(('time_span', '=', rec.time_span))
                
                target_records = self.env['target.achieve'].search(domain)
                target_count = len(target_records)

                #  directly use fields on target.achieve
                total_target = sum(ta.franchisee_target for ta in target_records)
                total_achieved = sum(ta.franchisee_achieved_amt for ta in target_records)

            rec.acc_man_target = total_target
            rec.acc_man_achieved_amt = total_achieved
            rec.acc_man_achieved_percent = (total_achieved / total_target * 100) if total_target else 0
            rec.manager_target_count = target_count
            rec.target_record_ids = target_records

    def action_view_manager_targets(self):
        """Open targets related to this account manager and time span"""
        self.ensure_one()

        domain = [ ]

        if self.time_span:
            domain.append(('time_span', '=', self.time_span))
        
        if self.acc_man_id:
            domain.append(('acc_man_id', '=', self.acc_man_id.id))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Franchisee Targets'),
            'res_model': 'target.achieve',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {'create': False},  # optional: prevent creating from this view
        }
    
class TargetAchieveProductSummary(models.Model):
    _name = "target.achieve.product.summary"
    _description = "Target Achieve Product Summary"

    target_achieve_id = fields.Many2one("target.achieve", ondelete="cascade")
    achieve_line_id = fields.Many2one("target.achieve.line", ondelete="cascade")

    product_id = fields.Many2one("product.product", required=True)
    qty = fields.Float("Quantity")
    amount = fields.Float("Amount")
