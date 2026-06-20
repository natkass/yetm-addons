from odoo import fields, models, api
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


# class CancelVendorBill(models.Model):
#     _inherit='account.move'
    
#     def change_bill_state(self):
#         cancel_bill= self.env['account.move'].search([('journal_id','=',77),('state','=','cancel')])
#         for c in cancel_bill:
#             _logger.info("+++++++++++++++++++++++")
#             _logger.info(c)
#             try:
#                 c.unlink()
#             except:
#                 pass
# class CancelPayment(models.Model):
#     _inherit='account.payment'
    
#     def change_vendor_payment(self):
#         cancel_payment= self.env['account.payment'].search([('payment_type','=','outbound'),('state','=','posted')])
#         for c in cancel_payment:
#             c.action_draft()
#             c.action_cancel()
#             c.unlink()
            
class ExtendProductt(models.Model):
    _inherit = 'product.template'
    products = fields.Selection([
        ('Seal', 'Seal'),
        ('Fabric', 'Fabric'),
        ('Fasha', 'Fasha'),
        ('Foam', 'Foam'),
        ('Bonded','Bonded'),
        ('Glue','Glue'),
        ('Tape Edge','Tape Edge'),
        # ('Sound Proof','Sound Proof')
    ], string='I Foam')
    fasha_related = fields.Many2one('product.template', string='Related Fabric', required_if_products='Fabric')
    no_rounding = fields.Boolean('No Rounding', default=False)

    fasha_related2 = fields.Many2one('product.product', string='Related Fabric', required_if_products='Fabric')


   # fasha_ids = fields.Many2many('product.product', 'fasha_relation','owner','related',string='Fashas', required_if_products='Fabric',
   #                               domain="[('products', '=', 'Fasha')]")


class ExtendProductt2(models.Model):
    _inherit = 'product.product'
    fasha_ids = fields.Many2many('product.product', 'fasha_relation','owner','related',string='Fashas', required_if_products='Fabric',
                                 domain="[('products', '=', 'Fasha')]")


class ExtendMrp(models.Model):
    _inherit = 'mrp.production'
    _order = 'id desc'  # Ensure we get the latest record first

    isNOnStandard = fields.Boolean(string="From Non-standard", default=False)
    length = fields.Float(string="Length", default=0.0, digits=(16, 2))
    width = fields.Float(string="Width", default=0.0, digits=(16, 2))
    height = fields.Float(string="Height", default=0.0, digits=(16, 2))
    description = fields.Char(string="Description")
    
    def _get_sequence(self, sequence_code, prefix, company_id):
        """Get or create a sequence with proper error handling"""
        try:
            Sequence = self.env['ir.sequence'].sudo()
            
            # Try to find existing sequence
            sequence = Sequence.search([
                ('code', '=', sequence_code),
                '|',
                ('company_id', '=', False),
                ('company_id', '=', company_id)
            ], limit=1)
            
            if not sequence:
                # Create new sequence if it doesn't exist
                sequence_vals = {
                    'name': f'Manufacturing Order BAZAR {company_id}',
                    'code': sequence_code,
                    'prefix': prefix,
                    'suffix': '',
                    'padding': 5,
                    'number_next': 1,
                    'number_increment': 1,
                    'company_id': company_id,
                    'use_date_range': False,
                }
                sequence = Sequence.create(sequence_vals)
                _logger.info("Created new sequence %s for company %s", sequence_code, company_id)
                
            return sequence
            
        except Exception as e:
            _logger.error("Error in _get_sequence: %s", str(e), exc_info=True)
            return None

    def _get_next_serial_number(self, prefix):
        """Generate the next available serial number for manufacturing orders"""
        try:
            # First try to get a sequence from the standard Odoo sequence
            try:
                seq = self.env['ir.sequence'].next_by_code('mrp.production')
                if seq:
                    return seq
            except Exception as e:
                _logger.warning("Could not get standard MO sequence: %s", str(e))
            
            # Fallback: Create a simple sequence based on current count + 1
            try:
                last_mo = self.env['mrp.production'].search(
                    [('name', 'like', f'{prefix}%')],
                    order='id desc',
                    limit=1
                )
                if last_mo and last_mo.name.startswith(prefix):
                    # Extract the number part and increment
                    import re
                    match = re.search(r'\d+', last_mo.name[len(prefix):])
                    if match:
                        next_num = int(match.group()) + 1
                        return f"{prefix}{next_num:05d}"
                
                # If no previous MO found, start with 1
                return f"{prefix}00001"
                
            except Exception as e:
                _logger.error("Error in fallback sequence generation: %s", str(e))
                # Last resort: use timestamp
                timestamp = fields.Datetime.now().strftime('%y%m%d%H%M%S')
                return f"{prefix}{timestamp}"
                
        except Exception as e:
            _logger.critical("Critical error in _get_next_serial_number: %s", str(e))
            # Final fallback: use timestamp with random suffix
            import random
            timestamp = fields.Datetime.now().strftime('%y%m%d%H%M%S')
            random_suffix = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=4))
            return f"{prefix}{timestamp}-{random_suffix}"

    @api.model
    def create(self, vals):
        _logger.info("\n=== [MO CREATION] Starting Manufacturing Order Creation ===")
        _logger.info("[MO CREATION] Initial values received: %s", vals)
        _logger.info("[MO CREATION] Environment: Database=%s, User=%s, Company=%s", 
                    self.env.cr.dbname, self.env.user.name, self.env.company.name)
        
        try:
            # Make a copy of the original values to avoid modifying the original
            create_vals = dict(vals)
            
            # Handle non-standard order data
            sale_name = create_vals.get('origin')
            if sale_name and not create_vals.get('isNOnStandard'):
                _logger.info("\n[MO CREATION] Processing sale order origin: %s", sale_name)
                _logger.info("[MO CREATION] Current create_vals before processing: %s", create_vals)
                
                # Check if this is a non-standard order
                sale = self.env['sale.order'].search([('name', '=', sale_name)], limit=1)
                if sale and sale.non_standard:
                    _logger.info("[MO CREATION] Non-standard order detected, skipping automatic MO creation")
                    # Return a dummy MO that will be handled by action_confirm
                    create_vals.update({
                        'isNOnStandard': True,
                        'state': 'draft',
                        'product_qty': max(1.0, create_vals.get('product_qty', 1.0)),  # Ensure positive quantity
                    })
            
            # Generate a name if not provided
            if not create_vals.get('name'):
                _logger.info("\n[MO CREATION] No name provided, generating MO name...")
                prefix = 'BAZAR/MO/'
                _logger.info(f"[MO CREATION] Calling _get_next_serial_number with prefix: {prefix}")
                mo_name = self._get_next_serial_number(prefix)
                _logger.info(f"[MO CREATION] Generated MO name: {mo_name}")
                create_vals['name'] = mo_name
                _logger.info("[MO CREATION] Assigned name to create_vals")
            
            _logger.info(f"\n[MO CREATION] Final values before MO creation: {create_vals} ")
            
            # Call parent create with the final values
            try:
                _logger.info("[MO CREATION] Calling parent create() with values: %s", create_vals)
                mo = super(ExtendMrp, self).create(create_vals)
                _logger.info("\n[MO CREATION] SUCCESS - Created MO ID: %s, Name: %s, State: %s", 
                           mo.id, mo.name, mo.state)
                if mo.product_id:
                    _logger.info("[MO CREATION] MO Details - Product: %s, Qty: %s %s, BOM: %s",
                               mo.product_id.display_name, mo.product_qty, 
                               mo.product_uom_id.name if mo.product_uom_id else '',
                               mo.bom_id.display_name if mo.bom_id else 'None')
                return mo
            except Exception as create_error:
                _logger.critical("\n[MO CREATION] FAILED - Error in parent create(): %s", str(create_error), exc_info=True)
                _logger.critical("[MO CREATION] Error type: %s", type(create_error).__name__)
                _logger.critical("[MO CREATION] Attempting fallback with minimal required fields...")
                
                # Get default UoM if not provided - use safer approach
                try:
                    default_uom = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
                    default_uom_id = default_uom.id if default_uom else None
                except Exception:
                    # Fallback: search for unit UoM directly
                    default_uom_rec = self.env['uom.uom'].search([('name', '=', 'Unit')], limit=1)
                    default_uom_id = default_uom_rec.id if default_uom_rec else None
                
                minimal_vals = {
                    'name': create_vals.get('name', f"BAZAR/MO/ERR-{fields.Datetime.now().strftime('%Y%m%d%H%M%S%f')}"),
                    'product_id': create_vals.get('product_id'),
                    'product_qty': create_vals.get('product_qty', 1.0),
                    'product_uom_id': create_vals.get('product_uom_id', default_uom_id),
                    'bom_id': create_vals.get('bom_id', False),
                }
                _logger.warning("[MO CREATION] Trying fallback with minimal values: %s", minimal_vals)
                return super(ExtendMrp, self).create(minimal_vals)
            
        except Exception as e:
            _logger.critical("CRITICAL ERROR in MO creation: %s", str(e), exc_info=True)
            
            # Last resort: create with minimal required fields
            try:
                # Get default UoM safely
                try:
                    default_uom_id = self.env.ref('uom.product_uom_unit', raise_if_not_found=False).id
                except Exception:
                    default_uom_rec = self.env['uom.uom'].search([('name', '=', 'Unit')], limit=1)
                    default_uom_id = default_uom_rec.id if default_uom_rec else None
                
                minimal_vals = {
                    'name': f"BAZAR/MO/CRIT-{fields.Datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    'product_id': vals.get('product_id'),
                    'product_qty': max(1.0, vals.get('product_qty', 1.0)),  # Ensure positive quantity
                    'product_uom_id': vals.get('product_uom_id', default_uom_id),
                    'bom_id': vals.get('bom_id', False),
                }
                return super(ExtendMrp, self).create(minimal_vals)
            except Exception as final_error:
                _logger.error("FATAL: Could not create MO even with minimal values: %s", str(final_error))
                raise
#
#         type = res.products
#         if type == 'Seal':
#             model = 'non_standard.seal'
#         elif type == 'Fabric':
#             model = 'non_standard.fabric'
#         elif type == 'Foam':
#             model = 'non_standard.value'
#         elif type == 'Fasha':
#             model = 'non_standard.fasha'
#         else:
#             return res
#         dd = self.env[model].create({
#             'unit_price': res.list_price,
#             'name': res.display_name,
#             'product': res.id
#         })
#         return res
#
#     @api.model
#     def write(self, vals):
#         res = super(ExtendProductt2, self).write(vals)
#         return res
#
#     @api.onchange('list_price')
#     def _onchange_valueof_this(self):
#         print('in meeee')
#         type = self.products
#         model = ''
#         if type == 'Seal':
#             model = 'non_standard.seal'
#         elif type == 'Fabric':
#             model = 'non_standard.fabric'
#         elif type == 'Foam':
#             model = 'non_standard.value'
#         elif type == 'Fasha':
#             model = 'non_standard.fasha'
#         if model == '':
#             return
#         else:
#             tem = self.env[model].search([])
#             for x in tem:
#                 print(x.id)
#             model = self.env[model].search([('product', '=', self.id)])
#             model.write(
#                 {
#                     'unit_price': self.list_price
#                 }
#             )



# class ManufacturingExtendNonStandard(models.Model):
#     _inherit = 'product.template'
#
#
#
#     shape = fields.Selection([
#         ('Rectangular', 'Rectangular'),
#         ('Circular', 'Circular'),
#         ('Triangular', 'Triangular')
#     ], 'Shape', default='Rectangular')
#     length = fields.Integer(string="Length", default=1)
#     width = fields.Integer(string="Width", default=1)
#     height = fields.Integer(string="Height", default=1)
#
#
#
#     @api.model
#     def create(self, vals):
#         res = super(ExtendProductt2, self).create(vals)
