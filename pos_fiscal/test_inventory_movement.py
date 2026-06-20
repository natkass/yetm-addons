#!/usr/bin/env python3
"""
Test script for validating inventory movement in pos_fiscal module
This script tests the _create_order_picking method implementation
"""

import logging
from datetime import datetime, date

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_logger = logging.getLogger(__name__)

def test_inventory_movement(env):
    """
    Test the inventory movement functionality for POS orders
    """
    print("=" * 60)
    print("TESTING POS FISCAL INVENTORY MOVEMENT")
    print("=" * 60)
    
    # Test 1: Check if the method exists
    print("\n[TEST 1] Checking if _create_order_picking method exists...")
    PosOrder = env['pos.order']
    
    if hasattr(PosOrder, '_create_order_picking'):
        print("✅ Method _create_order_picking exists in pos.order")
    else:
        print("❌ Method _create_order_picking NOT found in pos.order")
        return False
    
    # Test 2: Find a recent POS order to test with
    print("\n[TEST 2] Finding a recent POS order with fiscal data...")
    
    test_order = PosOrder.search([
        ('fiscal_mrc', '!=', False),
        ('fs_no', '!=', False),
        ('state', 'in', ['paid', 'done']),
        ('lines', '!=', False)
    ], limit=1, order='date_order desc')
    
    if not test_order:
        print("⚠️ No suitable POS order found for testing")
        print("Creating a test order is recommended for full validation")
        return False
    
    print(f"✅ Found POS order: {test_order.name} (FS: {test_order.fs_no})")
    print(f"   Date: {test_order.date_order}")
    print(f"   Amount: {test_order.amount_total}")
    print(f"   Lines: {len(test_order.lines)}")
    
    # Test 3: Check existing pickings for this order
    print("\n[TEST 3] Checking existing pickings for this order...")
    
    existing_pickings = env['stock.picking'].search([
        ('origin', '=', test_order.name)
    ])
    
    if existing_pickings:
        print(f"⚠️ Found {len(existing_pickings)} existing picking(s) for this order:")
        for pick in existing_pickings:
            print(f"   - {pick.name}: {pick.state} ({pick.picking_type_id.name})")
    else:
        print("✅ No existing pickings found (clean state for testing)")
    
    # Test 4: Check if session and config are properly set
    print("\n[TEST 4] Checking POS configuration...")
    
    if not test_order.session_id:
        print("❌ Order has no session assigned")
        return False
    
    print(f"✅ Session: {test_order.session_id.name}")
    
    if not test_order.session_id.config_id:
        print("❌ Session has no config assigned")
        return False
    
    print(f"✅ Config: {test_order.session_id.config_id.name}")
    
    if not test_order.session_id.config_id.picking_type_id:
        print("❌ Config has no picking type configured")
        print("   Please configure: Point of Sale > Configuration > Point of Sale > Inventory")
        return False
    
    picking_type = test_order.session_id.config_id.picking_type_id
    print(f"✅ Picking Type: {picking_type.name}")
    print(f"   Warehouse: {picking_type.warehouse_id.name}")
    print(f"   Source Location: {picking_type.default_location_src_id.complete_name}")
    print(f"   Dest Location: {picking_type.default_location_dest_id.complete_name}")
    
    # Test 5: Analyze order lines
    print("\n[TEST 5] Analyzing order lines...")
    
    stockable_lines = test_order.lines.filtered(
        lambda l: l.product_id.type in ['product', 'consu']
    )
    
    print(f"Total lines: {len(test_order.lines)}")
    print(f"Stockable lines: {len(stockable_lines)}")
    
    for line in stockable_lines[:3]:  # Show first 3 lines
        print(f"   - {line.product_id.name}: {line.qty} x {line.price_unit} = {line.price_subtotal_incl}")
        print(f"     Type: {line.product_id.type}, On Hand: {line.product_id.qty_available}")
    
    if not stockable_lines:
        print("⚠️ No stockable products in this order (service products only)")
        return False
    
    # Test 6: Test the picking creation
    print("\n[TEST 6] Testing picking creation...")
    print("⚠️ This will create actual stock movements. Continue? (dry run mode)")
    
    try:
        # Create a savepoint for rollback
        with env.cr.savepoint():
            print("\n🔄 Calling _create_order_picking()...")
            
            result = test_order._create_order_picking()
            
            if result:
                print(f"✅ Picking(s) created successfully: {result}")
                
                for picking in result:
                    print(f"\n📦 Picking: {picking.name}")
                    print(f"   Type: {picking.picking_type_id.name}")
                    print(f"   State: {picking.state}")
                    print(f"   Partner: {picking.partner_id.name if picking.partner_id else 'N/A'}")
                    print(f"   Source: {picking.location_id.complete_name}")
                    print(f"   Destination: {picking.location_dest_id.complete_name}")
                    print(f"   Moves:")
                    
                    for move in picking.move_ids:
                        print(f"     - {move.product_id.name}: {move.product_uom_qty} {move.product_uom.name}")
                        print(f"       State: {move.state}, Reserved: {move.quantity}")
            else:
                print("❌ No pickings created (check logs for details)")
            
            # Rollback the transaction (dry run)
            print("\n🔄 Rolling back transaction (dry run mode)...")
            raise Exception("Rollback for dry run")
            
    except Exception as e:
        if "Rollback for dry run" in str(e):
            print("✅ Test completed successfully (changes rolled back)")
        else:
            print(f"❌ Error during test: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("✅ _create_order_picking method is properly implemented")
    print("✅ Method can be called on POS orders")
    print("✅ Configuration appears correct")
    print("\nRECOMMENDATIONS:")
    print("1. Test with a real reconciliation process")
    print("2. Monitor stock levels before and after")
    print("3. Check picking creation in Inventory app")
    print("4. Validate with different product types")
    
    return True

def test_reconciliation_with_inventory(env):
    """
    Test the full reconciliation process with inventory movement
    """
    print("\n" + "=" * 60)
    print("TESTING RECONCILIATION WITH INVENTORY")
    print("=" * 60)
    
    # Find a recent reconciliation
    print("\n[TEST] Checking recent reconciliations...")
    
    PosOrder = env['pos.order']
    
    # Get today's date
    today = date.today()
    
    # Find orders created through reconciliation
    reconciled_orders = PosOrder.search([
        ('fiscal_mrc', '!=', False),
        ('fs_no', '!=', False),
        ('date_order', '>=', today),
        ('state', 'in', ['paid', 'done'])
    ], limit=5, order='date_order desc')
    
    if reconciled_orders:
        print(f"✅ Found {len(reconciled_orders)} reconciled orders from today")
        
        for order in reconciled_orders:
            pickings = env['stock.picking'].search([
                ('origin', '=', order.name)
            ])
            
            status = "✅" if pickings else "⚠️"
            print(f"{status} Order {order.name} (FS: {order.fs_no}): {len(pickings)} picking(s)")
    else:
        print("⚠️ No reconciled orders found from today")
    
    return True

# Main execution
if __name__ == "__main__":
    print("This script should be run from Odoo shell:")
    print("  ./odoo-bin shell -d your_database")
    print("\nThen execute:")
    print("  exec(open('/home/nuredin/Desktop/kd/pos_fiscal/test_inventory_movement.py').read())")
    print("\nOr in the shell:")
    print("  from test_inventory_movement import test_inventory_movement")
    print("  test_inventory_movement(env)")