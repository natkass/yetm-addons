from odoo import models, fields

class CustomerTaxWizard(models.TransientModel):
    _name = 'customer.tax.wizard'
    _description = 'Customer Invoice Tax Report Wizard'

    date_from = fields.Date(string="Start Date", required=True)
    date_to = fields.Date(string="End Date", required=True)


    def generate_report(self):
        data = {
            'form': self.read(['date_from', 'date_to'])[0]
        }
        return self.env.ref('erca_monthly_tax_report.report_customer_tax_xlsx').report_action(self, data=data)


