# -*- coding: utf-8 -*-

from . import controllers
from . import models
from . import report

def post_init_hook(env):
    ResConfig = env['res.config.settings']
    default_values = ResConfig.default_get(list(ResConfig.fields_get()))

    # Case 1: Enable a group
    default_values.update({'group_multi_currency': True})
    ResConfig.create(default_values).execute()

    # Set default params for HS Code attribute visibility
    env['ir.config_parameter'].sudo().set_param('import_fees.cid_visible', True)
    env['ir.config_parameter'].sudo().set_param('import_fees.exm_visible', True)
    env['ir.config_parameter'].sudo().set_param('import_fees.surcharge_visible', True)
    env['ir.config_parameter'].sudo().set_param('import_fees.pal_visible', True)
    env['ir.config_parameter'].sudo().set_param('import_fees.eic_visible', True)
    env['ir.config_parameter'].sudo().set_param('import_fees.cess_levy_visible', True)
    env['ir.config_parameter'].sudo().set_param('import_fees.excise_duty_visible', True)
    env['ir.config_parameter'].sudo().set_param('import_fees.ridl_visible', True)
    env['ir.config_parameter'].sudo().set_param('import_fees.srl_visible', True)
    env['ir.config_parameter'].sudo().set_param('import_fees.sscl_visible', True)
    env['ir.config_parameter'].sudo().set_param('import_fees.vat_visible', True)
    env['ir.config_parameter'].sudo().set_param('import_fees.customs_bill_visible', True)
    env['ir.config_parameter'].sudo().set_param('import_fees.shipping_bill_visible', True)
    env['ir.config_parameter'].sudo().set_param('import_fees.add_10pc_cif', False)
