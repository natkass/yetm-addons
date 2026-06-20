from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class ManufacturingRequestBatchReportWizard(models.TransientModel):
    _name = "manufacturing.request.batch.report.wizard"
    _description = "Batch Lifecycle Report Wizard"

    date_from = fields.Date(string="Start Date", required=True, default=fields.Date.today)
    date_to = fields.Date(string="End Date", required=True, default=fields.Date.today)
    branch_id = fields.Many2one("res.branch", string="Branch")

    def action_print_lifecycle_batch(self):
        """Generate batch lifecycle report for selected filters"""
        domain = [
            ('create_date', '>=', self.date_from),
            ('create_date', '<=', self.date_to + timedelta(days=1)),
        ]
        if self.branch_id:
            domain.append(('branch_id', '=', self.branch_id.id))

        requests = self.env['manufacturing.request'].search(domain)
        if not requests:
            raise UserError("No manufacturing requests found for the selected filters.")

        # Compute KPIs
        total_requests = len(requests)
        delayed_requests = sum(1 for r in requests if r.promise_date and r.promise_date < fields.Datetime.now() and r.state != 'delivered')

        # Average hours per stage across requests
        stage_totals = {}
        stage_counts = {}
        for r in requests:
            for stage in r.get_stage_durations():
                stage_name = stage['stage']
                stage_totals[stage_name] = stage_totals.get(stage_name, 0) + stage['hours']
                stage_counts[stage_name] = stage_counts.get(stage_name, 0) + 1
        avg_stage_hours = {k: (stage_totals[k] / stage_counts[k]) if stage_counts[k] else 0 for k in stage_totals}

        kpis = {
            'total_requests': total_requests,
            'delayed_requests': delayed_requests,
            'avg_stage_hours': avg_stage_hours,
        }

        return self.env.ref('manufacturing_request.action_report_lifecycle_batch').report_action(
            requests, data={'kpis': kpis}
        )
