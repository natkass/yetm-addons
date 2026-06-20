# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class CroppingInsects(models.Model):
    _name = 'cropping.insects'

    name = fields.Char(
        string = 'Name',
        required= True
    )
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
