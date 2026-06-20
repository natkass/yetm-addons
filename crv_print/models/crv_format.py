from odoo import api, fields, models


class CRVFormat(models.Model):
    _name = 'crv.format'
    _description = "Create CRV Format"

    name = fields.Char(string="CRV Name", required=True)
    ac_pay_margin_top = fields.Char()
    ac_pay_margin_left = fields.Char()
    ac_pay_letter_space = fields.Char()
    ac_pay_rotate = fields.Char(string='Rotation Text')
    ac_pay_css = fields.Char(string='Letter Spacing(ac_pay)')
    font_size = fields.Char(string="Font Size", default="20")
    font_css = fields.Char()
    
    
    date_margin_top = fields.Char()
    date_margin_left = fields.Char()
    date_letter_space = fields.Char()
    date_css = fields.Char()
    
    
    name_margin_top = fields.Char(string='Top Margin')
    name_margin_left = fields.Char(string='Left Margin')
    name_letter_space = fields.Char(string='Letter Spacing')
    name_css = fields.Char()
    
    
    tin_margin_top = fields.Char()
    tin_margin_left = fields.Char()
    tin_letter_space = fields.Char()
    tin_css = fields.Char()
    
    
    reason_margin_top = fields.Char()
    reason_margin_left = fields.Char()
    reason_letter_space = fields.Char()
    reason_css = fields.Char()
 
    amount_digit_top = fields.Char()
    amount_digit_left = fields.Char()
    amount_digit_letter_space = fields.Char()
    amount_digit_css = fields.Char()
    
    amount_total_amount_top = fields.Char()
    amount_total_amount_left = fields.Char()
    amount_total_amount_space = fields.Char()
    amount_total_amount_css = fields.Char()

    amount_vat_top = fields.Char()
    amount_vat_left = fields.Char()
    amount_vat_space = fields.Char()
    amount_vat_css = fields.Char()

    amount_word_top = fields.Char()
    amount_word_left = fields.Char()
    amount_word_letter_space = fields.Char()
    amount_word_css = fields.Char()
    
    whtamount_top = fields.Char()
    whtamount_left = fields.Char()
    whtamount_letter_space = fields.Char()
    whtamount_css = fields.Char()
    
    payment_mode_margin_top = fields.Char()
    payment_mode_margin_left = fields.Char()
    payment_mode_letter_space = fields.Char()
    payment_mode_css = fields.Char()
    
    document_margin_top = fields.Char()
    document_margin_left = fields.Char()
    document_letter_space = fields.Char()
    document_css = fields.Char()
    
    
    user_margin_top = fields.Char()
    user_margin_left = fields.Char()
    user_css = fields.Char()
    user_letter_space = fields.Char()

    @api.onchange( 
        'ac_pay_margin_top', 'ac_pay_margin_left', 'ac_pay_letter_space', 'ac_pay_rotate', 'font_size', 
        
        'date_margin_top', 'date_margin_left', 'date_letter_space', 
        
        'name_margin_top',  'name_margin_left', 'name_letter_space',
        
        'tin_margin_top', 'tin_margin_left', 'tin_letter_space',
        
        'reason_margin_top', 'reason_margin_left', 'reason_letter_space',
        
        'amount_digit_top', 'amount_digit_left','amount_digit_letter_space', 

        'amount_vat_top', 'amount_vat_left', 'amount_vat_space',

        'amount_total_amount_top', 'amount_total_amount_left', 'amount_total_amount_space',
        
        'amount_word_top', 'amount_word_left', 'amount_word_letter_space',

        'whtamount_top', 'whtamount_left', 'whtamount_letter_space',
        
        'payment_mode_margin_top', 'payment_mode_margin_left','payment_mode_letter_space', 
        
        'document_margin_top', 'document_margin_left', 'document_letter_space',
        
       'user_margin_top', 'user_margin_left','user_letter_space')
    def _compute_config(self):
        ac_pay_css = name_css = tin_css = reason_css = date_css = amount_digit_css = amount_word_css=whtamount_css = payment_mode_css = document_css= user_css = amount_vat_css = amount_total_amount_css =  ''
        if self.font_size:
            self.font_css = 'font-size:' + self.font_size + 'px;'

        if self.ac_pay_margin_top:
            ac_pay_css += 'margin-top:' + self.ac_pay_margin_top + 'px;'
        if self.ac_pay_margin_left:
            ac_pay_css += 'margin-left:' + self.ac_pay_margin_left + 'px;'
        if self.ac_pay_letter_space:
            ac_pay_css += 'letter-spacing:' + self.ac_pay_letter_space + 'px;'
        if self.ac_pay_rotate:
            ac_pay_css += 'transform: rotate(' + self.ac_pay_rotate + 'deg);-webkit-transform:rotate(' + self.ac_pay_rotate + 'deg);'
        self.ac_pay_css = ac_pay_css



        if self.date_margin_top:
            date_css += 'margin-top:' + self.date_margin_top + 'px;'
        if self.date_margin_left:
            date_css += 'margin-left:' + self.date_margin_left + 'px;'
        if self.date_letter_space:
            date_css += 'letter-spacing:' + self.date_letter_space + 'px;'
        self.date_css = date_css
        
        if self.name_margin_top:
            name_css += 'margin-top:' + self.name_margin_top + 'px;'
        if self.name_margin_left:
            name_css += 'margin-left:' + self.name_margin_left + 'px;'
        if self.name_letter_space:
            name_css += 'letter-spacing:' + self.name_letter_space + 'px;'
        self.name_css = name_css

        if self.document_margin_top:
            document_css += 'margin-top:' + self.document_margin_top + 'px;'
        if self.document_margin_left:
            document_css += 'margin-left:' + self.document_margin_left + 'px;'
        if self.document_letter_space:
            document_css += 'letter-spacing:' + self.document_letter_space + 'px;'
        self.document_css = document_css



        if self.reason_margin_top:
            reason_css += 'margin-top:' + self.reason_margin_top + 'px;'
        if self.reason_margin_left:
            reason_css += 'margin-left:' + self.reason_margin_left + 'px;'
        if self.reason_letter_space:
            reason_css += 'letter-spacing:' + self.reason_letter_space + 'px;'
        self.reason_css = reason_css

        if self.tin_margin_top:
            tin_css += 'margin-top:' + self.tin_margin_top + 'px;'
        if self.tin_margin_left:
            tin_css += 'margin-left:' + self.tin_margin_left + 'px;'
        if self.tin_letter_space:
            tin_css += 'letter-spacing:' + self.tin_letter_space + 'px;'
        self.tin_css = tin_css
        

        if self.amount_digit_top:
            amount_digit_css += 'margin-top:' + self.amount_digit_top + 'px;'
        if self.amount_digit_left:
            amount_digit_css += 'margin-left:' + self.amount_digit_left + 'px;'
        if self.amount_digit_letter_space:
            amount_digit_css += 'letter-spacing:' + self.amount_digit_letter_space + 'px;'
        self.amount_digit_css = amount_digit_css

        if self.amount_total_amount_top:
            amount_total_amount_css += 'margin-top:' + self.amount_total_amount_top + 'px;'
        if self.amount_total_amount_left:
            amount_total_amount_css += 'margin-left:' + self.amount_total_amount_left + 'px;'
        if self.amount_total_amount_space:
            amount_total_amount_css += 'letter-spacing:' + self.amount_total_amount_space + 'px;'
        self.amount_total_amount_css = amount_total_amount_css

        if self.amount_vat_top:
            amount_vat_css += 'margin-top:' + self.amount_vat_top + 'px;'
        if self.amount_vat_left:
            amount_vat_css += 'margin-left:' + self.amount_vat_left + 'px;'
        if self.amount_vat_space:
            amount_vat_css += 'letter-spacing:' + self.amount_vat_space + 'px;'
        self.amount_vat_css = amount_vat_css

        if self.amount_word_top:
            amount_word_css += 'margin-top:' + self.amount_word_top + 'px;'
        if self.amount_word_left:
            amount_word_css += 'margin-left:' + self.amount_word_left + 'px;'
        if self.amount_word_letter_space:
            amount_word_css += 'letter-spacing:' + self.amount_word_letter_space + 'px;'
        self.amount_word_css = amount_word_css 
        
        if self.whtamount_top:
            whtamount_css += 'margin-top:' + self.whtamount_top + 'px;'
        if self.whtamount_left:
            whtamount_css += 'margin-left:' + self.whtamount_left + 'px;'
        if self.whtamount_letter_space:
            whtamount_css += 'letter-spacing:' + self.whtamount_letter_space + 'px;'
        self.whtamount_css = whtamount_css
        
        
        if self.payment_mode_margin_top:
            payment_mode_css += 'margin-top:' + self.payment_mode_margin_top + 'px;'
        if self.payment_mode_margin_left:
            payment_mode_css += 'margin-left:' + self.payment_mode_margin_left + 'px;'
        if self.payment_mode_letter_space:
            payment_mode_css += 'letter-spacing:' + self.payment_mode_letter_space + 'px;'
        self.payment_mode_css = payment_mode_css

        if self.document_margin_top:
            document_css += 'margin-top:' + self.document_margin_top + 'px;'
        if self.document_margin_left:
            document_css += 'margin-left:' + self.document_margin_left + 'px;'
        if self.document_letter_space:
            document_css += 'letter-spacing:' + self.document_letter_space + 'px;'
        self.document_css = document_css


        if self.user_margin_top:
            user_css += 'margin-top:' + self.user_margin_top + 'px;'
        if self.user_margin_left:
            user_css += 'margin-left:' + self.user_margin_left + 'px;'
        if self.user_letter_space:
            user_css += 'letter-spacing:' + self.user_letter_space + 'px;'
        self.user_css = user_css




class account_payment(models.Model):
    _inherit = "account.payment"

    crv_format = fields.Many2one('crv.format', string="CRV Print format")
