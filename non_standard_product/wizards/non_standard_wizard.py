# wizard/non_standard_wizard.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ProductProduct(models.Model):
    _inherit = 'product.template'

    config_summary = fields.Text(string="Configuration Summary", readonly=True)

class NonStandardWizard(models.TransientModel):
    _name = "non.standard.wizard"
    _description = "Non Standard Product Configurator"

    order_id = fields.Many2one("sale.order", required=True)

    length = fields.Float("Length (cm)", required=True)
    width = fields.Float("Width (cm)", required=True)
    height = fields.Float("Height (cm)", required=True)

    rounded_length_cm = fields.Float(string="Rounded Length", readonly=True)
    rounded_width_cm = fields.Float(string="Rounded Width", readonly=True)
    rounded_height_cm = fields.Float(string="Rounded Height", readonly=True)

    volume_m3 = fields.Float(string="Calculated Volume (m³)", compute="_compute_values", store=True, digits=(16, 3))

    description = fields.Char(string="Description", compute="_compute_values", store=True, readonly=True)

    # Rounding Length
    @staticmethod
    def _round_length(value):
        rules = [
            (21, 30, 30), (31, 40, 40), (41, 50, 50), (51, 65, 65),
            (66, 75, 75), (76, 80, 80), (81, 100, 100), (101, 120, 120),
            (121, 150, 150), (151, 160, 160), (161, 190, 190), (191, 200, 200)
        ]
        for low, high, rounded in rules:
            if low <= value <= high:
                return rounded
        return value
    
    # Rounding Width
    @staticmethod
    def _round_width(value):
        rules = [
            (21, 30, 30), (31, 40, 40), (41, 50, 50), (51, 65, 65),
            (66, 75, 75), (76, 80, 80), (81, 100, 100), (101, 120, 120),
            (121, 150, 150), (151, 160, 160), (161, 180, 180),
            (181, 190, 190), (191, 200, 200)
        ]
        for low, high, rounded in rules:
            if low <= value <= high:
                return rounded
        return value
    
    # Rounding Height
    @staticmethod
    def _round_height(value):
        rules = [
            (21, 30, 30), (31, 40, 40), (41, 50, 50), (51, 65, 65),
            (66, 75, 75), (76, 80, 80), (81, 100, 100), (101, 120, 120),
            (121, 150, 150), (151, 160, 160), (161, 180, 180),
            (181, 190, 190), (191, 200, 200)
        ]
        for low, high, rounded in rules:
            if low <= value <= high:
                return rounded
        return value
    



    has_packrise = fields.Boolean(string='Packrise')
    packrise = fields.Float("Packrise", required=True)

    
    shape_id = fields.Many2one("non.standard.shape", string="Shape", domain=[('state', '=', 'lock')])
    has_foam = fields.Boolean(string='Foam')
    foam_type_id = fields.Many2one('non.standard.foam', string="Foam Type", domain=[('state', '=', 'lock')])
    foam_value_id = fields.Many2one('non.standard.foam.value', string="Value", domain="[('foam_id', '=', foam_type_id)]")
    foam_size = fields.Float("Size",  compute="_compute_foam_values", store=True)
    foam_unit_price = fields.Float("Unit Price", compute="_compute_foam_values", store=True)
    foam_total_price = fields.Float("Total",  compute="_compute_foam_values", store=True)

    # --- UI Level: Immediate feedback ---
    # @api.onchange('packrise', 'height')
    # def _onchange_packrise(self):
    #     for rec in self:
    #         if rec.packrise and rec.height and rec.packrise > rec.height:
    #             # Reset to the max allowed instead of letting invalid input stay
    #             rec.packrise = rec.height
    #             return {
    #                 'warning': {
    #                     'title': "Invalid Packrise",
    #                     'message': f"Packrise cannot exceed the Rounded Height ({rec.height} cm). It has been adjusted automatically.",
    #                 }
    #             }

    # --- Backend safeguard: prevents invalid saves ---
    @api.constrains('packrise', 'height')
    def _check_packrise(self):
        for rec in self:
            if rec.packrise and rec.height and rec.packrise > rec.height:
                raise ValidationError(
                    f"Packrise cannot exceed the Rounded Height ({rec.height} cm)."
                )

    # Foam
    @api.depends('length', 'width', 'height', 'rounded_length_cm', 'rounded_width_cm', 'foam_value_id', 'packrise', 'has_packrise')
    def _compute_foam_values(self):
        for rec in self:
            # Apply rounding rules and save to separate fields
            rec.rounded_length_cm = self._round_length(rec.length) if rec.length else 0.0
            rec.rounded_width_cm = self._round_width(rec.width) if rec.width else 0.0
            # rec.rounded_height_cm = self._round_height(rec.height) if rec.height else 0.0

            if rec.length and rec.width and rec.height:
                # Apply new volume formula
                base_volume = (
                (rec.rounded_length_cm / 100) *
                (rec.rounded_width_cm / 100) *
                (rec.height / 100)
                )
                if rec.has_packrise:
                    # New formula with packrise
                    rec.volume_m3 = base_volume * ((rec.packrise + rec.height) / (2 * rec.height))
                else:
                    # Normal volume
                    rec.volume_m3 = base_volume
            else:
                rec.volume_m3 = 0.0

            rec.foam_unit_price = rec.foam_value_id.unit_price if rec.foam_value_id else 0.0
            rec.foam_total_price = rec.foam_unit_price * rec.volume_m3
            rec.description = "Unit Amount: {:.2f}; Calculated Volume: {:.3f} m³".format(
                rec.foam_unit_price, rec.volume_m3
            )

    has_fabric = fields.Boolean(string='Fabric')
    fabric_type_id = fields.Many2one('non.standard.fabric', string="Fabric Type", domain=[('state', '=', 'lock')])
    
    fabric_size = fields.Float(string="Size", compute="_compute_fabric_values", store=True)
    fabric_unit_price = fields.Float(string="Unit price", compute="_compute_fabric_values", store=True)
    
    fabric_total_price = fields.Float("Total",  compute="_compute_fabric_values", store=True)

    @api.onchange('has_fabric')
    def _onchange_has_fabric(self):
        if not self.has_fabric:
            self.fabric_type_id = False
            self.fabric_value_id = False

    # Fabric
    @api.depends('length', 'width', 'rounded_length_cm','rounded_width_cm', 'fabric_type_id')
    def _compute_fabric_values(self):
        for rec in self:
            rec.rounded_length_cm = self._round_length(rec.length) if rec.length else 0.0
            rec.rounded_width_cm = self._round_width(rec.width) if rec.width else 0.0

            if rec.rounded_length_cm and rec.rounded_width_cm :
                rec.fabric_size = ((rec.rounded_length_cm / 100) * (rec.rounded_width_cm / 100)) + 0.08
            else:
                rec.fabric_size = 0.0

            rec.fabric_unit_price = rec.fabric_type_id.unit_price if rec.fabric_type_id else 0.0
            rec.fabric_total_price = rec.fabric_unit_price * rec.fabric_size

    has_corner = fields.Boolean(string='Corner')
    has_fabric_value = fields.Boolean(string='Fasha', related='has_fabric', store=True)
    fabric_value_id = fields.Many2one('non.standard.fabric.value', string="Fasha", domain="[('fabric_id', '=', fabric_type_id)]")
    fabric_value_size = fields.Float("Size", compute="_compute_fasha_values", store=True)
    fabric_value_unit_price = fields.Float("Unit Price", compute="_compute_fasha_values", store=True)
    fabric_value_total_price = fields.Float("Total", compute="_compute_fasha_values", store=True)

    # Fasha
    @api.depends('length', 'width', 'rounded_length_cm', 'rounded_width_cm', 'fabric_value_id', 'has_corner')
    def _compute_fasha_values(self):
        for rec in self:
            size = 0.0

            if rec.length and rec.width:
                size = (((rec.length / 100) + (rec.width / 100)) * 2) + 0.04

                # add 0.12 if has_corner is checked
                if rec.has_corner:
                    size += 0.12

            rec.fabric_value_size = size
            rec.fabric_value_unit_price = rec.fabric_value_id.unit_price if rec.fabric_value_id else 0.0
            rec.fabric_value_total_price = rec.fabric_value_unit_price * size


    has_seal = fields.Boolean(string='Seal')
    seal_type_id = fields.Many2one('non.standard.seal', string="Seal", domain=[('state', '=', 'lock')])
    seal_size = fields.Float("Size", compute="_compute_seal_values", store=True)
    seal_unit_price = fields.Float("Unit Price", compute="_compute_seal_values", store=True)
    seal_total_price = fields.Float("Total", compute="_compute_seal_values", store=True)

    @api.onchange('has_seal')
    def _onchange_has_seal(self):
        if not self.has_seal:
            self.seal_type_id = False
            

    # Seal
    @api.depends('length', 'width', 'rounded_length_cm','rounded_width_cm', 'seal_type_id')
    def _compute_seal_values(self):
        for rec in self:
            rec.rounded_length_cm = self._round_length(rec.length) if rec.length else 0.0
            rec.rounded_width_cm = self._round_width(rec.width) if rec.width else 0.0

            if rec.rounded_length_cm or rec.rounded_width_cm:
                rec.seal_size = max(rec.rounded_length_cm, rec.rounded_width_cm) / 100
            else:
                rec.seal_size = 0.0

            rec.seal_unit_price = rec.seal_type_id.unit_price if rec.seal_type_id else 0.0
            rec.seal_total_price = rec.seal_unit_price * rec.seal_size


    has_glue = fields.Boolean(string='Glue')
    glue_type_id = fields.Many2one('non.standard.glue', string="Glue", domain=[('state', '=', 'lock')])
    glue_qty = fields.Float("Qty", compute="_compute_glue_values", store=True)
    glue_unit_price = fields.Float("Unit Price", compute="_compute_glue_values", store=True)
    glue_total_price = fields.Float("Total", compute="_compute_glue_values", store=True)

    @api.onchange('has_glue')
    def _onchange_has_glue(self):
        if not self.has_glue:
            self.glue_type_id = False

    # Glue
    @api.depends('length', 'width', 'rounded_length_cm','rounded_width_cm', 'glue_type_id')
    def _compute_glue_values(self):
        for rec in self:
            rec.rounded_length_cm = self._round_length(rec.length) if rec.length else 0.0
            rec.rounded_width_cm = self._round_width(rec.width) if rec.width else 0.0

            if rec.rounded_length_cm and rec.rounded_width_cm :
                rec.glue_qty = (0.75) * (rec.rounded_length_cm / 100) * (rec.rounded_width_cm / 100)
            else:
                rec.glue_qty = 0.0

            rec.glue_unit_price = rec.glue_type_id.unit_price if rec.glue_type_id else 0.0
            rec.glue_total_price = rec.glue_unit_price * rec.glue_qty

    has_tape = fields.Boolean(string='Tape Edge')
    tape_type_id = fields.Many2one('non.standard.tape', string="Tape Edge", domain=[('state', '=', 'lock')])
    tape_qty = fields.Float("Qty", compute="_compute_tape_values", store=True)
    tape_unit_price = fields.Float("Unit Price", compute="_compute_tape_values", store=True)
    tape_total_price = fields.Float("Total", compute="_compute_tape_values", store=True)

    @api.onchange('has_tape')
    def _onchange_has_tape(self):
        if not self.has_tape:
            self.tape_type_id = False

    # Tape Edge
    @api.depends('length', 'width', 'rounded_length_cm','rounded_width_cm', 'tape_type_id')
    def _compute_tape_values(self):
        for rec in self:
            rec.rounded_length_cm = self._round_length(rec.length) if rec.length else 0.0
            rec.rounded_width_cm = self._round_width(rec.width) if rec.width else 0.0

            if rec.rounded_length_cm and rec.rounded_width_cm :
                rec.tape_qty = 0.04 *((rec.rounded_length_cm) + (rec.rounded_width_cm))
            else:
                rec.tape_qty = 0.0

            rec.tape_unit_price = rec.tape_type_id.unit_price if rec.tape_type_id else 0.0
            rec.tape_total_price = rec.tape_unit_price * rec.tape_qty

    # line_ids = fields.One2many("non.standard.wizard.line", "wizard_id", string="Parameters")
    subtotal = fields.Float(compute="_compute_subtotal", store=True)



    @api.depends('tape_total_price', 'glue_total_price', 'seal_total_price', 'fabric_value_total_price', 'fabric_total_price', 'foam_total_price')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = sum([
                rec.tape_total_price,
                rec.glue_total_price,
                rec.seal_total_price,
                rec.fabric_value_total_price,
                rec.fabric_total_price,
                rec.foam_total_price
            ])

    
    def action_clear(self):
        for rec in self:
            # reset all your input fields here
            
            rec.length = False
            rec.width = False
            rec.height = False
            rec.foam_type_id = False
            rec.foam_value_id = False
            rec.has_packrise = False
            rec.has_fabric = False
            rec.has_corner = False
            rec.has_seal = False
            rec.has_glue = False           
            rec.has_tape = False
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',   # keeps it as a wizard
        }
            
            

    def action_add_to_order(self):
        self.ensure_one()

        def fmt(value):
            return f"{value:.2f}".rstrip('0').rstrip('.') if value else '-'


        # Generate product name
        seq = self.env["ir.sequence"].next_by_code("non.standard.product")
        name_parts = []
        # Add shape if present
        if self.shape_id:
            name_parts.append(self.shape_id.name)
        
        if self.foam_type_id:
            name_parts.append(self.foam_type_id.name)

        if self.fabric_type_id:
            name_parts.append(self.fabric_type_id.name)

        if self.tape_type_id:
            name_parts.append(f"({self.tape_type_id.name})")

        dims = []
        if self.length:
            dims.append(str(fmt(self.length)))
        if self.width:
            dims.append(str(fmt(self.width)))
        if self.height:
            dims.append(str(fmt(self.height)))
        if dims:
            name_parts.append("x".join(dims))

        if getattr(self, "has_packrise", False):
            name_parts.append(f"/ {(str(fmt(self.height)))}")
        
        # Combine all parts
        product_name = " ".join(name_parts)

        non_standard_tag = self.env["product.tag"].search([("name", "=", "Non-Standard")], limit=1)
        if not non_standard_tag:
            non_standard_tag = self.env["product.tag"].create({"name": "Non-Standard"})


        # After creating the product
        config_summary = f"""
        Dimensions: {fmt(self.length) if self.length else '-'} x {fmt(self.width) if self.width else '-'} x {fmt(self.height) if self.height else '-'}
        Has Packrise: {'Yes' if getattr(self, 'has_packrise', False) else 'No'}
        Shape: {self.shape_id.name if self.shape_id else '-'}
        Foam Type: {self.foam_type_id.name if self.foam_type_id else '-'}
        Fabric Type: {self.fabric_type_id.name if self.fabric_type_id else '-'}
        Fasha Type: {self.fabric_value_id.name if self.fabric_value_id else '-'}
        Has Corner: {'Yes' if getattr(self, 'has_corner', False) else 'No'}
        Seal Type: {self.seal_type_id.name if self.seal_type_id else '-'}
        Glue Type: {self.glue_type_id.name if self.glue_type_id else '-'}       
        Tape Type: {self.tape_type_id.name if self.tape_type_id else '-'}       
        
        Subtotal: {self.subtotal}
        """
        
        # Create the configured product
        product = self.env["product.product"].create({
            "name": product_name,
            "default_code": seq,
            "barcode": seq,
            "list_price": self.subtotal,
            "type": "product",
            "config_summary": config_summary.strip(),
            "product_tag_ids": [(6, 0, [non_standard_tag.id])],
        })

        # Collect BOM lines
        bom_lines = []

        # Define material types with attributes for quantity calculation
        material_types = [
            {"field": "foam_type_id", "enabled": True, "qty_field": "volume_m3"},
            {"field": "fabric_type_id", "enabled": self.has_fabric, "qty_field": "fabric_size"},
            {"field": "fabric_value_id", "enabled": True, "qty_field": "fabric_value_size"},
            {"field": "seal_type_id", "enabled": self.has_seal, "qty_field": "seal_size"},
            {"field": "glue_type_id", "enabled": self.has_glue, "qty_field": "glue_qty"},
            {"field": "tape_type_id", "enabled": self.has_tape, "qty_field": "tape_qty"},
        ]

        for mat in material_types:
            mat_obj = getattr(self, mat["field"], False)
            if mat["enabled"] and mat_obj and getattr(mat_obj, "product_ids", False):
                qty_value = getattr(self, mat["qty_field"], 0.0)
                for mapping in mat_obj.product_ids:
                    qty = mapping.bom_factor * qty_value
                    bom_lines.append((0, 0, {
                        "product_id": mapping.product_id.id,
                        "product_qty": qty,
                    }))

        # Create the BoM only if there are BOM lines
        if bom_lines:
            self.env["mrp.bom"].create({
                "product_tmpl_id": product.product_tmpl_id.id,
                "product_qty": 1,
                "type": "normal",
                "bom_line_ids": bom_lines,
            })

        # Add to Sale Order
        self.order_id.order_line.create({
            "order_id": self.order_id.id,
            "product_id": product.id,
            "product_uom_qty": 1,
            "price_unit": self.subtotal,
        })

        return {"type": "ir.actions.act_window_close"}

    