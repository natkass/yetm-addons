from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HarmonizedCode(models.Model):
    _name = 'import_fees.harmonized_code'
    _description = 'Harmonized System Code'
    
    name = fields.Char('HS Code', required=True)
    company_ids = fields.Many2many('res.company', string='Companies')
    com_value = fields.Float('COM', required=True, default=0.0, help="Cost of Manufacture (fixed amount per hs code)")
    exm_value = fields.Float('EXM', required=True, default=0.0, help="Export Market Value (fixed amount per hs code)")
    cid_rate = fields.Float('CID', required=True, default=0.0, help="Customs Import Duty Rate")
    surcharge_rate = fields.Float('Surcharge', required=True, default=0.0, help="Surcharge Rate")
    pal_rate = fields.Float('PAL', required=True, default=0.0, help="Port Authority Levy Rate")
    eic_rate = fields.Float('EIC', required=True, default=0.0, help="Export Inspection Charge Rate")
    cess_levy_rate = fields.Float('Cess Levy', required=True, default=0.0, help="Cess Levy Rate")
    excise_duty_rate = fields.Float('Excise Duty', required=True, default=0.0, help="Excise Duty Rate")
    ridl_rate = fields.Float('RIDL', required=True, default=0.0, help="Road Infrastructure Development Levy Rate")
    srl_rate = fields.Float('SRL', required=True, default=0.0, help="Sugar Re-planting Levy Rate")
    sscl_rate = fields.Float('SSCL', required=True, default=0.0, help="Special Sales Tax on Cigarettes and Liquor Rate")
    vat_rate = fields.Float('VAT', required=True, default=0.15, help="Value Added Tax Rate")
    is_com_visible = fields.Boolean('COM Visible', compute='_compute_com_visible', store=False)
    is_exm_visible = fields.Boolean('EXM Visible', compute='_compute_exm_visible', store=False)
    is_cid_visible = fields.Boolean('CID Visible', compute='_compute_cid_visible', store=False)
    is_surcharge_visible = fields.Boolean('Surcharge Visible', compute='_compute_surcharge_visible', store=False)
    is_pal_visible = fields.Boolean('PAL Visible', compute='_compute_pal_visible', store=False)
    is_eic_visible = fields.Boolean('EIC Visible', compute='_compute_eic_visible', store=False)
    is_cess_levy_visible = fields.Boolean('Cess Levy Visible', compute='_compute_cess_levy_visible', store=False)
    is_excise_duty_visible = fields.Boolean('Excise Duty Visible', compute='_compute_excise_duty_visible', store=False)
    is_ridl_visible = fields.Boolean('RIDL Visible', compute='_compute_ridl_visible', store=False)
    is_srl_visible = fields.Boolean('SRL Visible', compute='_compute_srl_visible', store=False)
    is_sscl_visible = fields.Boolean('SSCL Visible', compute='_compute_sscl_visible', store=False)
    is_vat_visible = fields.Boolean('VAT Visible', compute='_compute_vat_visible', store=False)

    product_category_ids = fields.One2many(
        comodel_name="product.category",
        inverse_name="harmonized_code_id",
        string="Product Categories",
        readonly=True,
    )
    product_template_ids = fields.One2many(
        comodel_name="product.template",
        inverse_name="harmonized_code_id",
        string="Products",
        readonly=True,
    )
    product_category_count = fields.Integer(compute="_compute_product_category_count")
    product_template_count = fields.Integer(compute="_compute_product_template_count")

    @api.model
    def get_harmonized_codes_for_company(self, company_id):
        result = self.search([
            '|', ('company_ids', '=', False),
            ('company_ids', 'in', [company_id])
        ])
        return result

    @api.constrains('name', 'company_ids')
    def _check_unique_name(self):
        for record in self:
            domain = [('name', '=', record.name)]
            if record.company_ids:
                domain += [('company_ids', 'in', record.company_ids.ids)]
            else:
                domain += [('company_ids', '=', False)]
            
            if record.id:
                domain += [('id', '!=', record.id)]
            
            if self.search_count(domain) > 0:
                raise ValidationError(
                    "The HS Code name must be unique for the selected companies "
                    "or globally if no company is selected."
                )

    def _compute_com_visible(self):
        for code in self:
            code.is_com_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.com_visible', False)

    def _compute_exm_visible(self):
        for code in self:
            code.is_exm_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.exm_visible', False)

    def _compute_cid_visible(self):
        for code in self:
            code.is_cid_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.cid_visible', False)

    def _compute_surcharge_visible(self):
        for code in self:
            code.is_surcharge_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.surcharge_visible', False)

    def _compute_pal_visible(self):
        for code in self:
            code.is_pal_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.pal_visible', False)

    def _compute_eic_visible(self):
        for code in self:
            code.is_eic_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.eic_visible', False)

    def _compute_cess_levy_visible(self):
        for code in self:
            code.is_cess_levy_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.cess_levy_visible', False)

    def _compute_excise_duty_visible(self):
        for code in self:
            code.is_excise_duty_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.excise_duty_visible', False)

    def _compute_ridl_visible(self):
        for code in self:
            code.is_ridl_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.ridl_visible', False)

    def _compute_srl_visible(self):
        for code in self:
            code.is_srl_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.srl_visible', False)

    def _compute_sscl_visible(self):
        for code in self:
            code.is_sscl_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.sscl_visible', False)

    def _compute_vat_visible(self):
        for code in self:
            code.is_vat_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.vat_visible', False)

    @api.model
    def _default_company_id(self):
        return False

    @api.depends("product_category_ids")
    def _compute_product_category_count(self):
        for code in self:
            code.product_category_count = len(code.product_category_ids)

    @api.depends("product_template_ids")
    def _compute_product_template_count(self):
        for code in self:
            code.product_template_count = len(code.product_template_ids)

    @api.model
    def find_or_create(self, hs_code):
        harmonized_code = self.search([('name', '=', hs_code)], limit=1)
        if not harmonized_code:
            harmonized_code = self.create({'name': hs_code})
        return harmonized_code


class CustomsFees(models.Model):
    _name = "import_fees.customs_fees"
    _order = "harmonized_code_id"
    _description = "Customs Fees"
    harmonized_code_id = fields.Many2one('import_fees.harmonized_code', "HS Code")
    landed_costs_id = fields.Many2one('stock.landed.cost', "Landed Costs")
    rate = fields.Float("Rate")
    state = fields.Selection(related='landed_costs_id.state', string='Status', readonly=True, store=True)
    local_currency_id = fields.Many2one(related='landed_costs_id.currency_id', string='Local Currency',
                                        readonly=True, store=True)
    value = fields.Monetary("Declared Value", currency_field='local_currency_id')
    amount = fields.Monetary("Customs Duties", currency_field='local_currency_id',
                             digits='Product Price', compute='_compute_amount', store=True)
    com_value = fields.Monetary("COM", currency_field='local_currency_id')
    exm_value = fields.Monetary("EXM", currency_field='local_currency_id')
    cif_value = fields.Monetary("CIF", currency_field='local_currency_id')
    cid_value = fields.Monetary("CID", currency_field='local_currency_id')
    surcharge_value = fields.Monetary("Surcharge", currency_field='local_currency_id')
    pal_value = fields.Monetary("PAL", currency_field='local_currency_id')
    eic_value = fields.Monetary("EIC", currency_field='local_currency_id')
    cess_levy_value = fields.Monetary("Cess Levy", currency_field='local_currency_id')
    excise_duty_value = fields.Monetary("Excise Duty", currency_field='local_currency_id')
    ridl_value = fields.Monetary("RIDL", currency_field='local_currency_id')
    srl_value = fields.Monetary("SRL", currency_field='local_currency_id')
    sscl_value = fields.Monetary("SSCL", currency_field='local_currency_id')
    vat_value = fields.Monetary("VAT", currency_field='local_currency_id')
    is_com_visible = fields.Boolean('COM Visible', compute='_compute_com_visible', store=False)
    is_exm_visible = fields.Boolean('EXM Visible', compute='_compute_exm_visible', store=False)
    is_cid_visible = fields.Boolean('CID Visible', compute='_compute_cid_visible', store=False)
    is_surcharge_visible = fields.Boolean('Surcharge Visible', compute='_compute_surcharge_visible', store=False)
    is_pal_visible = fields.Boolean('PAL Visible', compute='_compute_pal_visible', store=False)
    is_eic_visible = fields.Boolean('EIC Visible', compute='_compute_eic_visible', store=False)
    is_cess_levy_visible = fields.Boolean('Cess Levy Visible', compute='_compute_cess_levy_visible', store=False)
    is_excise_duty_visible = fields.Boolean('Excise Duty Visible', compute='_compute_excise_duty_visible', store=False)
    is_ridl_visible = fields.Boolean('RIDL Visible', compute='_compute_ridl_visible', store=False)
    is_srl_visible = fields.Boolean('SRL Visible', compute='_compute_srl_visible', store=False)
    is_sscl_visible = fields.Boolean('SSCL Visible', compute='_compute_sscl_visible', store=False)
    is_vat_visible = fields.Boolean('VAT Visible', compute='_compute_vat_visible', store=False)



    def _compute_com_visible(self):
        for code in self:
            code.is_com_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.com_visible', False)

    def _compute_exm_visible(self):
        for code in self:
            code.is_exm_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.exm_visible', False)

    def _compute_cid_visible(self):
        for code in self:
            code.is_cid_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.cid_visible', False)

    def _compute_surcharge_visible(self):
        for code in self:
            code.is_surcharge_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.surcharge_visible', False)

    def _compute_pal_visible(self):
        for code in self:
            code.is_pal_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.pal_visible', False)

    def _compute_eic_visible(self):
        for code in self:
            code.is_eic_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.eic_visible', False)

    def _compute_cess_levy_visible(self):
        for code in self:
            code.is_cess_levy_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.cess_levy_visible', False)

    def _compute_excise_duty_visible(self):
        for code in self:
            code.is_excise_duty_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.excise_duty_visible', False)

    def _compute_ridl_visible(self):
        for code in self:
            code.is_ridl_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.ridl_visible', False)

    def _compute_srl_visible(self):
        for code in self:
            code.is_srl_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.srl_visible', False)

    def _compute_sscl_visible(self):
        for code in self:
            code.is_sscl_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.sscl_visible', False)

    def _compute_vat_visible(self):
        for code in self:
            code.is_vat_visible = self.env['ir.config_parameter'].sudo().get_param('import_fees.vat_visible', False)

    def _compute_tariffs(self):
        tariffs = self.landed_costs_id.calculate_tariffs(self.harmonized_code_id, old_value=self)
        self.com_value = tariffs['com_value'] if not self.com_value else self.com_value
        self.exm_value = tariffs['exm_value'] if not self.exm_value else self.exm_value
        self.cid_value = tariffs['cid_value'] if not self.cid_value else self.cid_value
        self.surcharge_value = tariffs['surcharge_value'] if not self.surcharge_value else self.surcharge_value
        self.pal_value = tariffs['pal_value'] if not self.pal_value else self.pal_value
        self.eic_value = tariffs['eic_value']   if not self.eic_value else self.eic_value
        self.cess_levy_value = tariffs['cess_levy_value']   if not self.cess_levy_value else self.cess_levy_value
        self.excise_duty_value = tariffs['excise_duty_value'] if not self.excise_duty_value else self.excise_duty_value
        self.ridl_value = tariffs['ridl_value'] if not self.ridl_value else self.ridl_value
        self.srl_value = tariffs['srl_value'] if not self.srl_value else self.srl_value
        self.sscl_value = tariffs['sscl_value'] if not self.sscl_value else self.sscl_value
        self.vat_value = tariffs['vat_value'] if not self.vat_value else self.vat_value
        self.cif_value = tariffs['cif_value'] if not self.cif_value else self.cif_value
        self.rate = tariffs['rate']
        self.amount = tariffs['amount']
        self.value = tariffs['value']

    @api.depends('cif_value', 'eic_value', 'pal_value', 'surcharge_value',
                 'cid_value', 'exm_value', 'com_value', 'cess_levy_value',
                 'excise_duty_value', 'ridl_value', 'srl_value', 'sscl_value', 'vat_value')
    def _compute_amount(self):
        for record in self:
            record.amount = record.com_value + record.exm_value + record.cid_value \
                + record.surcharge_value + record.pal_value + record.eic_value + \
                    record.cess_levy_value + record.excise_duty_value + record.ridl_value + \
                        record.srl_value + record.sscl_value
