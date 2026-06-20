# delivery_print_limit/models/ir_actions_report.py
from odoo import models, fields, _
from odoo.exceptions import UserError

class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    # Known report_name values for Delivery Slip
    DELIVERY_REPORT_NAMES = (
        "stock.report_deliveryslip",  # default
        "stock.report_picking",       # sometimes used
    )

    # REPLACE your _render_qweb_pdf in models/ir_actions_report.py with this

    # Replace your _render_qweb_pdf with this (no ensure_one; handles model/record calls)

    def _render_qweb_pdf(self, *args, **kwargs):
        # Normalize args from various callers (report_xlsx, core, etc.)
        res_ids = kwargs.get("res_ids")
        data = kwargs.get("data")
        reportname = None

        if len(args) == 1 and res_ids is None and isinstance(args[0], (list, tuple, set, int)):
            res_ids = args[0]
        elif len(args) >= 2:
            if isinstance(args[0], str):
                # (reportname, res_ids, [data])
                reportname = args[0]
                if res_ids is None:
                    res_ids = args[1]
                if data is None and len(args) >= 3:
                    data = args[2]
            else:
                # (res_ids, [data])
                if res_ids is None and isinstance(args[0], (list, tuple, set, int)):
                    res_ids = args[0]
                if data is None and len(args) >= 2:
                    data = args[1]

        if isinstance(res_ids, int):
            res_ids = [res_ids]

        # Get the report record if available; some callers invoke on the model (len(self) == 0)
        report_rec = self if len(self) == 1 else None
        if not report_rec and reportname:
            if hasattr(self, "_get_report_from_name"):
                report_rec = self._get_report_from_name(reportname)
            if not report_rec:
                report_rec = self.env["ir.actions.report"].search([("report_name", "=", reportname)], limit=1)

        # Only guard Delivery Slip PDFs on stock.picking
        if (
            report_rec
            and report_rec.model == "stock.picking"
            and report_rec.report_name in ("stock.report_deliveryslip", "stock.report_picking")
            and res_ids
        ):
            pickings = self.env["stock.picking"].browse(list(res_ids))
            outgoing = pickings.filtered(lambda p: p.picking_type_id.code == "outgoing")

            # Check limits
            for p in outgoing:
                limit = p.picking_type_id.allowed_delivery_prints or 0
                if limit and p.delivery_print_count >= limit:
                    from odoo.exceptions import UserError
                    raise UserError(
                        _("Delivery Slip for %(name)s has already been printed %(count)s time(s). "
                        "Limit is %(limit)s. Please contact a manager to reset the counter.") % {
                            "name": p.name, "count": p.delivery_print_count, "limit": limit
                        }
                    )

            # Increment counters
            now = fields.Datetime.now()
            for p in outgoing:
                limit = p.picking_type_id.allowed_delivery_prints or 0
                if not limit or p.delivery_print_count < limit:
                    p.sudo().write({
                        "delivery_print_count": p.delivery_print_count + 1,
                        "delivery_last_print_user_id": self.env.user.id,
                        "delivery_last_print_date": now,
                    })

        # Defer to core for actual rendering
        return super()._render_qweb_pdf(*args, **kwargs)
