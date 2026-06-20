from odoo import models, fields

# -------------------- FOAM --------------------
class NonStandardFoam(models.Model):
    _name = 'non.standard.foam'
    _description = 'Non-Standard Foam Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    value_ids = fields.One2many('non.standard.foam.value', 'foam_id', string="Values", tracking=True)
    product_ids = fields.One2many('non.standard.foam.product', 'foam_id', string="BOM Products", tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Verified'),
        ('lock', 'Locked'),
        ('cancel', 'Cancelled'),        
    ], default='draft', tracking=True)
    
    def action_verify(self):
        for record in self:
            record.write({'state': 'verify'})
            
            
    def action_lock(self):
        for record in self:
            record.write({'state': 'lock'})

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})

    def action_draft(self):
        for record in self:
            record.write({'state': 'draft'})
            


    
class NonStandardFoamValue(models.Model):
    _name = 'non.standard.foam.value'
    _description = 'Foam Type Value'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    unit_price = fields.Float(required=True, tracking=True)
    foam_id = fields.Many2one('non.standard.foam', required=True, tracking=True)
    

class NonStandardFoamProduct(models.Model):
    _name = 'non.standard.foam.product'
    _description = 'Foam - Product Mapping'

    
    product_id = fields.Many2one('product.product', string="BOM Product", required=True, tracking=True)
    bom_factor = fields.Float(string="BOM Factor", default=1.0, tracking=True)
    foam_id = fields.Many2one('non.standard.foam', required=True)


# -------------------- FABRIC --------------------
class NonStandardFabric(models.Model):
    _name = 'non.standard.fabric'
    _description = 'Non-Standard Fabric'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    unit_price = fields.Float(required=True, tracking=True)
    value_ids = fields.One2many('non.standard.fabric.value', 'fabric_id', string="Values", tracking=True)
    product_ids = fields.One2many('non.standard.fabric.product', 'fabric_id', string="BOM Products", tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Verified'),
        ('lock', 'Locked'),
        ('cancel', 'Cancelled'),        
    ], default='draft', tracking=True)

    def action_verify(self):
        for record in self:
            record.write({'state': 'verify'})
            
            
    def action_lock(self):
        for record in self:
            record.write({'state': 'lock'})

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})

    def action_draft(self):
        for record in self:
            record.write({'state': 'draft'})

class NonStandardFabricValue(models.Model):
    _name = 'non.standard.fabric.value'
    _description = 'Fasha Value'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    unit_price = fields.Float(required=True, tracking=True)
    fabric_id = fields.Many2one('non.standard.fabric', required=True, tracking=True)
    bom_factor = fields.Float(string="BOM Factor", default=1.0)
    # product_ids = fields.One2many('non.standard.fabric.product', 'fabric_value_id', string="BOM Products", tracking=True)


class NonStandardFabricProduct(models.Model):
    _name = 'non.standard.fabric.product'
    _description = 'Fabric - Product Mapping'

    fabric_id = fields.Many2one('non.standard.fabric', required=True, ondelete="cascade")
    product_id = fields.Many2one('product.product', string="BOM Product", required=True)
    bom_factor = fields.Float(string="BOM Factor", default=1.0)


# -------------------- SHAPE --------------------
class NonStandardShape(models.Model):
    _name = 'non.standard.shape'
    _description = 'Non-Standard Shape'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Verified'),
        ('lock', 'Locked'),
        ('cancel', 'Cancelled'),        
    ], default='draft', tracking=True)

    def action_verify(self):
        for record in self:
            record.write({'state': 'verify'})
            
            
    def action_lock(self):
        for record in self:
            record.write({'state': 'lock'})

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})

    def action_draft(self):
        for record in self:
            record.write({'state': 'draft'})




# -------------------- SEAL --------------------
class NonStandardSeal(models.Model):
    _name = 'non.standard.seal'
    _description = 'Non-Standard Seal'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    unit_price = fields.Float(required=True, tracking=True)
    product_ids = fields.One2many('non.standard.seal.product', 'seal_id', string="BOM Products", tracking=True)

    # value_ids = fields.One2many('non.standard.seal', 'seal_id', string="Values", tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Verified'),
        ('lock', 'Locked'),
        ('cancel', 'Cancelled'),        
    ], default='draft', tracking=True)

    def action_verify(self):
        for record in self:
            record.write({'state': 'verify'})
            
            
    def action_lock(self):
        for record in self:
            record.write({'state': 'lock'})

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})

    def action_draft(self):
        for record in self:
            record.write({'state': 'draft'})


class NonStandardSealProduct(models.Model):
    _name = 'non.standard.seal.product'
    _description = 'Seal - Product Mapping'

    seal_id = fields.Many2one('non.standard.seal', required=True, ondelete="cascade")
    product_id = fields.Many2one('product.product', string="BOM Product", required=True)
    bom_factor = fields.Float(string="BOM Factor", default=1.0)


# -------------------- GLUE --------------------
class NonStandardGlue(models.Model):
    _name = 'non.standard.glue'
    _description = 'Non-Standard Glue'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    unit_price = fields.Float(required=True, tracking=True)
    product_ids = fields.One2many('non.standard.glue.product', 'glue_id', string="BOM Products", tracking=True)

    # value_ids = fields.One2many('non.standard.glue', 'glue_id', string="Values", tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Verified'),
        ('lock', 'Locked'),
        ('cancel', 'Cancelled'),        
    ], default='draft', tracking=True)

    def action_verify(self):
        for record in self:
            record.write({'state': 'verify'})
            
            
    def action_lock(self):
        for record in self:
            record.write({'state': 'lock'})

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})

    def action_draft(self):
        for record in self:
            record.write({'state': 'draft'})


class NonStandardGlueProduct(models.Model):
    _name = 'non.standard.glue.product'
    _description = 'Glue - Product Mapping'

    glue_id = fields.Many2one('non.standard.glue', required=True, ondelete="cascade")
    product_id = fields.Many2one('product.product', string="BOM Product", required=True)
    bom_factor = fields.Float(string="BOM Factor", default=1.0)


# -------------------- TAPE --------------------
class NonStandardTape(models.Model):
    _name = 'non.standard.tape'
    _description = 'Non-Standard Tape'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    unit_price = fields.Float(required=True, tracking=True)
    product_ids = fields.One2many('non.standard.tape.product', 'tape_id', string="BOM Products", tracking=True)

    # value_ids = fields.One2many('non.standard.tape', 'tape_id', string="Values", tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Verified'),
        ('lock', 'Locked'),
        ('cancel', 'Cancelled'),        
    ], default='draft', tracking=True)

    def action_verify(self):
        for record in self:
            record.write({'state': 'verify'})
            
            
    def action_lock(self):
        for record in self:
            record.write({'state': 'lock'})

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})

    def action_draft(self):
        for record in self:
            record.write({'state': 'draft'})


class NonStandardTapeProduct(models.Model):
    _name = 'non.standard.tape.product'
    _description = 'Tape - Product Mapping'

    tape_id = fields.Many2one('non.standard.tape', required=True, ondelete="cascade")
    product_id = fields.Many2one('product.product', string="BOM Product", required=True)
    bom_factor = fields.Float(string="BOM Factor", default=1.0)


