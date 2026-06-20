# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    com_visible = fields.Boolean(string="Cost of Manufacture, fixed amount per hs code (COM)", config_parameter='import_fees.com_visible', default= False)
    exm_visible = fields.Boolean(string="Export Market Value fixed amount per hs code (EXM)", config_parameter='import_fees.exm_visible', default= False)
    cid_visible = fields.Boolean(string="Customs Import Duty Rate (CID)", config_parameter='import_fees.cid_visible', default= True)
    surcharge_visible = fields.Boolean(string="Surcharge Rate", config_parameter='import_fees.surcharge_visible', default= False)
    pal_visible = fields.Boolean(string="Port Authority Levy Rate (PAL)", config_parameter='import_fees.pal_visible', default= False)
    eic_visible = fields.Boolean(string="Export Inspection Charge Rate (EIC)", config_parameter='import_fees.eic_visible', default= False)
    cess_levy_visible = fields.Boolean(string="Cess Levy Rate", config_parameter='import_fees.cess_levy_visible', default=False)
    excise_duty_visible = fields.Boolean(string="Excise Duty Rate", config_parameter='import_fees.excise_duty_visible', default=False)
    ridl_visible = fields.Boolean(string="Road Infrastructure Development Levy Rate (RIDL)", config_parameter='import_fees.ridl_visible', default=False)
    srl_visible = fields.Boolean(string="Sugar Re-planting Levy Rate (SRL)", config_parameter='import_fees.srl_visible', default=False)
    sscl_visible = fields.Boolean(string="Special Sales Tax on Cigarettes and Liquor Rate (SSCL)", config_parameter='import_fees.sscl_visible', default=False)
    vat_visible = fields.Boolean(string="Value Added Tax Rate (VAT)", config_parameter='import_fees.vat_visible', default=True)
    customs_bill_visible = fields.Boolean(string="Generate Customs Bill from the Landed Costs", config_parameter='import_fees.customs_bill_visible', default=False)
    shipping_bill_visible = fields.Boolean(string="Generate Shipping Bill from the Landed Costs", config_parameter='import_fees.shipping_bill_visible', default=False)
    add_10pc_cif = fields.Boolean(string="Add 10% of CIF to VAT, CESS and SSCL calculations", config_parameter='import_fees.add_10pc_cif', default=False, company_dependent=True)
