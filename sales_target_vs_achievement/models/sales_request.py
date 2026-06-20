from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta



class SalesRequest(models.Model):
    _name = "sales.request"
    _description = "Sales Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Request Reference", 
                       required=True,                       
                       copy=False, 
                       readonly=True,                       
                       default="New")
    partner_id = fields.Many2one('res.partner', 
                                 string="Franchisee", 
                                 domain="[('category_id', 'ilike', 'Franchisee')]", 
                                 required=True, 
                                 help="Customer with Franchisee tag", 
                                 tracking=True)
    date_request = fields.Datetime(string="Request Date", default=fields.Datetime.now,readonly=True)
    
    expiration_date = fields.Datetime(
        string="Expiration", 
        default=lambda self: (fields.Datetime.now() + timedelta(days=3)).date(),
        readonly=True
    )
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    requested_by = fields.Many2one('res.users', string="Requested By", default=lambda s: s.env.user, readonly=True)
    verified_by = fields.Many2one('res.users', string="Verified By", readonly=True)
    approved_by = fields.Many2one('res.users', string="Approved By", readonly=True)
    dispatched_by = fields.Many2one('res.users', string="Dispatched By", readonly=True)
    

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('verified', 'Verified'),
        ('approved', 'Sale Approved'),        
        ('ready', 'Ready'),
        ('done', 'Done'),
        ('refused', 'Refused'),
        ('cancel', 'Cancelled'),
    ], string="Status", default='draft', tracking=True)

    pay_state = fields.Selection([
        ('waiting', 'Waiting'),        
        ('pay', 'Payment Verified'),        
    ], string="Payment Status", default='waiting', tracking=True)

    line_ids = fields.One2many('sales.request.line', 'request_id', string="Order Lines", copy=True)
    note = fields.Text(string="Notes")
    refusal_reason = fields.Text(string="Refusal Reason")
    discount = fields.Monetary(string='Discount Amount', compute='_compute_amounts', store=True, readonly=True)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', compute='_compute_amounts', store=True, readonly=True)
    amount_tax = fields.Monetary(string='Taxes', compute='_compute_amounts', store=True, readonly=True)
    amount_total = fields.Monetary(string='Total', compute='_compute_amounts', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # track who should act next (helper)
    next_actor_group = fields.Selection([
        ('sales_manager', 'Sales Manager'),
        ('marketing_manager', 'Marketing Manager'),
        ('dispatcher', 'Dispatcher'),
        ('account_manager', 'Account Manager'),
        ('none', 'None'),
    ], string="Next Actor", compute='_compute_next_actor', store=False)

    
    sale_order_id = fields.Many2one(
        'sale.order',
        string="Sales Order",
        readonly=True,
        copy=False,
    )

    sale_order_count = fields.Integer(
        string="Sales Orders",
        compute="_compute_sale_order_count",
    )

    def _compute_sale_order_count(self):
        for rec in self:
            rec.sale_order_count = 1 if rec.sale_order_id else 0

    def action_create_sale_order(self):
        self.ensure_one()

        if self.state != 'ready':
            raise UserError(_("Only requests in Ready state can create a Sales Order."))

        if self.sale_order_id:
            raise UserError(_("A Sales Order has already been created."))

        order_lines = []
        for line in self.line_ids:
            order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'product_uom_qty': line.quantity,
                'price_unit': line.price_unit,
                'discount': line.discount,
                'tax_id': [(6, 0, line.tax_id.ids)],
            }))

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'payment_term_id': self.payment_term_id.id,
            'origin': self.name,
            'order_line': order_lines,
        })

        self.sale_order_id = sale_order.id
        self.state = 'done'

        self.message_post(
            body=_("Sales Order <a href='#' data-oe-model='sale.order' data-oe-id='%d'>%s</a> created.")
            % (sale_order.id, sale_order.name)
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
        }

    def action_open_sale_order(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Order'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
        }
    
    def unlink(self):
        for rec in self:
            if rec.sale_order_id:
                raise UserError(_("You cannot delete a request linked to a Sales Order."))
        return super().unlink()

 

    
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/' or not vals.get('name'):
            seq = self.env['ir.sequence'].next_by_code('sales.request') or '/'
            vals['name'] = seq
        rec = super().create(vals)
        rec.message_post(body=_("Sales Request created by %s") % (rec.requested_by.name))
        return rec

    def _compute_next_actor(self):
        for rec in self:
            if rec.state == 'submitted':
                rec.next_actor_group = 'sales_manager'
            elif rec.state == 'verified':
                rec.next_actor_group = 'marketing_manager'
            elif rec.state == 'approved':
                rec.next_actor_group = 'dispatcher'
            elif rec.state == 'ready':
                rec.next_actor_group = 'account_manager'
            else:
                rec.next_actor_group = 'none'

   

    @api.depends(
        'line_ids.price_subtotal',
        'line_ids.tax_amount',
        'line_ids.discount',
        'line_ids.quantity',
        'line_ids.price_unit'
    )
    def _compute_amounts(self):
        for rec in self:
            untaxed = 0.0
            taxes = 0.0
            discount_total = 0.0

            for line in rec.line_ids:
                untaxed += line.price_subtotal
                taxes += line.tax_amount

                # Correct: discount computed from original price, not price_subtotal
                original_line_total = line.price_unit * line.quantity
                discount_total += original_line_total * (line.discount / 100.0)

            rec.amount_untaxed = untaxed
            rec.amount_tax = taxes
            rec.discount = discount_total
            rec.amount_total = untaxed + taxes

    # ---------- workflow buttons ----------
    def action_submit(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("You must add order lines before submitting."))
        self.state = 'submitted'
        # notify sales managers
        self.message_post(body=_("Request submitted by %s") % self.requested_by.name)
        self._notify_group('sales_target_vs_achievement.group_sales_request_sales_manager', _("New Sales Request to Verify"))
        

    def action_verify(self):
        self.ensure_one()
        self.state = 'verified'
        self.verified_by = self.env.user
        self.message_post(body=_("Request verified by %s") % self.verified_by.name)
        self._notify_group('sales_target_vs_achievement.group_sales_request_marketing_manager', _("Request verified — please approve"))
        self._clear_activities()

    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancel'               
        self._clear_activities()

    

    def action_approve(self):
        self.ensure_one()
        self.state = 'approved'
        self.approved_by = self.env.user
        self.message_post(body=_("Request approved by %s") % self.approved_by.name)
        self._notify_group('sales_target_vs_achievement.group_sales_request_dispatcher', _("Request approved — dispatcher, mark ready"))
        self._notify_group('sales_target_vs_achievement.group_sales_request_account_manager', _("Request approved — Account Managr, Contact Franchisee"))
        self._clear_activities()

    def action_pay(self):
        self.ensure_one()
        self.pay_state = 'pay'        
        self.message_post(body=_("Payment Verified  by %s") % self.approved_by.name)
        self._notify_group('sales_target_vs_achievement.group_sales_request_dispatcher', _("Payment Confirmed"))
        self._notify_group('sales_target_vs_achievement.group_sales_request_account_manager', _("Payment Confirmed"))
        self._clear_activities()

    def action_waiting(self):
        self.ensure_one()
        self.pay_state = 'waiting'       
        
        self._clear_activities()

    def action_mark_ready(self):
        self.ensure_one()
        self.state = 'ready'
        self.dispatched_by = self.env.user
        self.message_post(body=_("Request marked ready by %s") % self.dispatched_by.name)
        self._notify_group(None, _("Request is ready"))  # you can customize to notify account manager
        self._clear_activities()

    def action_done(self):
        self.ensure_one()
        self.state = 'done'
        self.message_post(body=_("Request completed by %s") % self.env.user.name)
        self._clear_activities()

    def action_refuse(self, reason=None):
        self.ensure_one()
        self.state = 'refused'
        if reason:
            self.refusal_reason = reason
        self.message_post(body=_("Request refused by %s. Reason: %s") % (self.env.user.name, self.refusal_reason or ''))
        # notify requester
        self._notify_user(self.requested_by, _("Your request was refused"))
        self._clear_activities()
        

    # ---------- helpers ----------
    def _notify_group(self, xml_id, subject):
        """Create a mail.activity for all users in security group (xml_id). If xml_id None, notify requester"""
        if not xml_id:
            return
        group = self.env.ref(xml_id, raise_if_not_found=False)
        if not group:
            return
        users = group.users
        for u in users:
            # create an activity for each user to action this request
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=u.id,
                note=subject,
            )

    def _notify_user(self, user, subject):
        if not user:
            return
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=user.id,
            note=subject,
        )
    def _mark_previous_activities_done(self):
        for record in self:
            activities = self.env['mail.activity'].search([
                ('res_model', '=', record._name),
                ('res_id', '=', record.id),
            ])
            for activity in activities:
                activity.action_feedback(feedback="Automatically marked as done due to status change.")

    def _clear_activities(self):
        self.activity_ids.unlink()

    def action_print_pdf(self):
        return self.env.ref('sales_target_vs_achievement.report_sales_request_pdf').report_action(self)
    


class SalesRequestLine(models.Model):
    _name = "sales.request.line"
    _description = "Sales Request Line"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    request_id = fields.Many2one('sales.request', string="Request", ondelete='cascade')
    
    product_id = fields.Many2one(
        'product.product',
        string="Product",
        domain=[('sale_ok', '=', True)],
        required=True
    )
    name = fields.Text(string="Description")
    quantity = fields.Float(string="Quantity", default=1.0)
    price_unit = fields.Monetary(string="Unit Price", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='request_id.currency_id', store=True, readonly=True)
    tax_id = fields.Many2many('account.tax', string="Taxes")
    price_subtotal = fields.Monetary(string="Subtotal", compute='_compute_subtotal', store=True)
    tax_amount = fields.Monetary(string="Tax Amount", compute='_compute_subtotal', store=True)
    discount = fields.Float(
        string="Discount (%)",
        digits='Discount',
        store=True, readonly=False, precompute=True)

    

    @api.depends('quantity', 'price_unit', 'discount', 'tax_id')
    def _compute_subtotal(self):
        for line in self:
            # Calculate base amount before tax and after discount
            price = line.price_unit * line.quantity
            discount_amount = price * (line.discount / 100.0)
            discounted_price = price - discount_amount

            # Compute tax amount
            tax_amount = 0.0
            for tax in line.tax_id:
                if tax.amount_type == 'percent':
                    tax_amount += discounted_price * (tax.amount / 100.0)
                elif tax.amount_type == 'fixed':
                    tax_amount += tax.amount * line.quantity

            # Assign computed values
            line.price_subtotal = discounted_price
            line.tax_amount = tax_amount    

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """ Auto-fill description, price, and taxes from product """
        if not self.product_id:
            return
        product = self.product_id

        # set description (use sales description if available)
        self.name = product.get_product_multiline_description_sale() or product.name

        # set price (depends on pricelist, but for now use list_price)
        self.price_unit = product.lst_price

        # set taxes from product (consider fiscal position if needed later)
        self.tax_id = [(6, 0, product.taxes_id.ids)]

    