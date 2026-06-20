from odoo import models, fields

class ERCAMonthlyTaxWizard(models.TransientModel):
    _name = 'erca.monthly.tax.wizard'
    _description = 'ERCA Monthly Tax Report Wizard'

    date_from = fields.Date(string="Start Date", required=True)
    date_to = fields.Date(string="End Date", required=True)


    def generate_report(self):
        data = {
            'form': self.read(['date_from', 'date_to'])[0]
        }
        return self.env.ref('erca_monthly_tax_report.report_erca_tax_xlsx').report_action(self, data=data)
