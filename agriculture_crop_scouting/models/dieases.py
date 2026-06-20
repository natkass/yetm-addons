# -*- coding: utf-8 -*-

from odoo import api, fields, models  


class CroppingDieases(models.Model):
    _name = 'cropping.dieases'

    name = fields.Char(
        string = 'Name',
        required= True
    )
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
