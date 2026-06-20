# -*- coding: utf-8 -*-
# from odoo import http


# class ProductHarmonizedSystemCosts(http.Controller):
#     @http.route('/import_fees/import_fees/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/import_fees/import_fees/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('import_fees.listing', {
#             'root': '/import_fees/import_fees',
#             'objects': http.request.env['import_fees.import_fees'].search([]),
#         })

#     @http.route('/import_fees/import_fees/objects/<model("import_fees.import_fees"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('import_fees.object', {
#             'object': obj
#         })
