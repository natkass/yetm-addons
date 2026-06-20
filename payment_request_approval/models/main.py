from email.policy import default
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class payment_category(models.Model):
     _inherit= 'approval.category'

     min_amount = fields.Float(string='Minimum Amount', help='Minimum amount allowed for this category')
     max_amount = fields.Float(string='Maximum Amount', help='Maximum amount allowed for this category')
     to_be_billed=fields.Boolean(string='Billed')
     advance = fields.Boolean(string='Advance')


class Payment_Request(models.Model):
    _inherit = 'approval.request'

    reciept_id = fields.Many2one('account.move', ondelete='cascade',
                                 string='Related Reciept', help='Reciept Related')
    payment_id = fields.Many2one('account.payment', ondelete='cascade', string='Related Payment', help='Payment Related')

    @api.model
    def create(self, vals):
        # Call the validation method before creating the record
        self._check_amount_in_range(vals)
        return super(Payment_Request, self).create(vals)

    def write(self, vals):
        # Call the validation method before saving the record
        self._check_amount_in_range(vals)
        return super(Payment_Request, self).write(vals)

    def _check_amount_in_range(self, vals):
        # Get the amount either from vals or from existing data
        amount = vals.get('amount', self.amount)
        category_id = self.category_id if not vals.get('category_id') else self.env['approval.category'].browse(vals.get('category_id'))

        # Check if the amount is within the category's min and max amount range
        if category_id and (category_id.min_amount > amount or category_id.max_amount < amount):
            raise UserError(_("The request amount must be between the minimum and maximum limits defined for this category."))


    def action_approve(self, approver=None):
        _logger.info("***************************************")

        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        _logger.info(approver.request_id)
        # _logger.info(approver.request_id.partner_id)
        # return True

        if approver.request_id.category_id.to_be_billed or approver.request_id.category_id.advance:
            _logger.info("#################################333")
            _logger.info(approver.user_id.x_studio_approve_payment_max)
            # if approver.request_id.amount > approver.user_id.x_studio_approve_payment_max:
            create_request = False
            _logger.info(approver.request_id.reciept_id)
            approver_list = []
            for each_approver in approver.request_id.approver_ids:
                _logger.info(each_approver.user_id.name)
                _logger.info(each_approver.id)
                approver_list.append({
                    "approver": each_approver,
                    "amount" : each_approver.user_id.x_studio_approve_payment_max
                })
            status_lst = approver.request_id.mapped('approver_ids.status')
               
            number_of_approves =status_lst.count('approved')
            minimal_approvers = len(status_lst)

            # _logger.info(approver_list)
            approver_list = sorted(approver_list, key=lambda d: d['amount']) 
            _logger.info(approver_list)
            if approver.request_id.reciept_id.id == False and number_of_approves == minimal_approvers - 1:
                            create_request = True;
            elif approver.request_id.reciept_id.id == False: 
                for a in approver_list:
                        # each_approver = self.env['approver.approver'].search(["id" , "=" , a.id])
                        _logger.info(a['approver'].id)
                        _logger.info(approver.id)
                        if a['approver'].status != "approved" and a['approver'].id != approver.id:
                            _logger.info("first_1")
                            create_request = False
                            break;
                        elif a['approver'].status == "approved" and a['approver'].id != approver.id:
                            _logger.info("first_2")
                            pass;
                        elif a['approver'].user_id.x_studio_approve_payment_max < approver.request_id.amount:
                            _logger.info("first")
                            create_request = False
                            break;
                        elif a['approver'].status != "approved" and a['approver'].id == approver.id: 
                            _logger.info("second")
                            create_request=True
                            break;
                        # elif a.id == approver.id:
                        #     create_request=True
                        #     break;
                        elif a['approver'].status == 'approved':
                            _logger.info("third")
                            pass
                        else:
                            create_request=False
                            _logger.info("forth")
                            break;
            _logger.info(create_request)
            # wsdgasdvh
            if create_request:
                _logger.info("########################################")
                
                if approver.request_id.category_id.to_be_billed:
                    journal = self.env['account.journal'].search([('type', "=", "purchase")], order="create_date asc", limit=1)
                    val = {
                        "journal_id": journal.id,
                        "move_type": "in_invoice",
                        "invoice_date": approver.request_id.date,
                        "date": approver.request_id.date,
                        "x_studio_payment_request": approver.request_id.id,
                    }
                    if approver.request_id.partner_id:
                        val['partner_id'] = approver.request_id.partner_id.id
                    if approver.request_id.reference:
                        val['contact_name'] = approver.request_id.reference
                    line_data = {
                        "account_id": journal.default_account_id.id,
                        "quantity": 1,
                        "price_unit": approver.request_id.amount,
                        "price_subtotal": approver.request_id.amount,
                        "partner_id": approver.request_id.partner_id.id,
                    }
                    val['invoice_line_ids'] = [(0, 0, line_data)]
                    result = self.env['account.move'].create(val)
                    approver.request_id.reciept_id = result.id
                    _logger.info(result)

                elif approver.request_id.category_id.advance:
                    journal = self.env['account.journal'].search([('type', '=', 'bank')], order='create_date asc', limit=1)
                    payment_vals = {
                        "payment_type": "outbound",
                        "partner_type": "supplier",
                        "partner_id": approver.request_id.partner_id.id,
                        "amount": approver.request_id.amount,
                        "journal_id": journal.id,
                        "date": approver.request_id.date,
                        "ref": approver.request_id.name,
                    }
                    payment = self.env['account.payment'].create(payment_vals)
                    approver.request_id.payment_id = payment.id
                    _logger.info(payment)

        approver.write({'status': 'approved'})
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()


class RecieptJournalEntry(models.Model):
    _inherit = "account.move"

    contact_name = fields.Char(string='Contact Name')
