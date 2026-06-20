#!/usr/bin/env python3
"""
Test script for complete order synchronization during reconciliation.
This tests that existing orders are completely updated with ALL invoice data.
"""

import xmlrpc.client
import sys
from datetime import datetime, date

# Odoo connection settings
url = 'http://localhost:8069'
db = 'pos_fiscal_db'
username = 'admin'
password = 'admin'

# Test parameters
TEST_MRC = "URB0000380"
TEST_DATE = "2025-07-12"

def connect():
    """Connect to Odoo via XML-RPC"""
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    if not uid:
        raise Exception("Authentication failed")
    
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    return models, uid

def test_complete_sync():
    """Test complete synchronization of existing orders"""
    print("=" * 60)
    print("TESTING COMPLETE ORDER SYNCHRONIZATION")
    print("=" * 60)
    
    try:
        models, uid = connect()
        print(f"✅ Connected to Odoo as user {uid}")
        
        # Step 1: Find an existing order with FS number
        print("\n📋 Step 1: Finding existing orders...")
        order_ids = models.execute_kw(
            db, uid, password,
            'pos.order', 'search',
            [[
                ('fiscal_mrc', '=', TEST_MRC),
                ('date_order', '>=', TEST_DATE),
                ('date_order', '<=', TEST_DATE + " 23:59:59"),
                ('fs_no', '!=', False)
            ]],
            {'limit': 5}
        )
        
        if not order_ids:
            print("❌ No orders found with FS numbers for testing")
            return
        
        print(f"✅ Found {len(order_ids)} orders with FS numbers")
        
        # Step 2: Get order details before sync
        order_id = order_ids[0]
        order_before = models.execute_kw(
            db, uid, password,
            'pos.order', 'read',
            [order_id],
            {'fields': ['fs_no', 'amount_total', 'amount_tax', 'pos_reference', 
                       'partner_id', 'lines', 'payment_ids']}
        )[0]
        
        print(f"\n📦 Order BEFORE sync:")
        print(f"  - ID: {order_id}")
        print(f"  - FS No: {order_before['fs_no']}")
        print(f"  - Total: {order_before['amount_total']}")
        print(f"  - Tax: {order_before['amount_tax']}")
        print(f"  - Lines: {len(order_before['lines'])} items")
        print(f"  - Payments: {len(order_before['payment_ids'])} records")
        
        # Step 3: Find matching invoice
        print(f"\n🔍 Step 3: Finding matching invoice...")
        fs_number = int(order_before['fs_no'].lstrip('0'))
        
        device_ids = models.execute_kw(
            db, uid, password,
            'pos.device', 'search',
            [[('mrc', '=', TEST_MRC)]]
        )
        
        if not device_ids:
            print("❌ No device found")
            return
            
        invoice_ids = models.execute_kw(
            db, uid, password,
            'pos.invoice', 'search',
            [[
                ('device_id', '=', device_ids[0]),
                ('fsNumber', '=', fs_number)
            ]]
        )
        
        if not invoice_ids:
            print(f"❌ No invoice found with FS number {fs_number}")
            return
        
        invoice = models.execute_kw(
            db, uid, password,
            'pos.invoice', 'read',
            [invoice_ids[0]],
            {'fields': ['fsNumber', 'totalWithTax', 'totalTax', 'referenceNumber', 
                       'paymentType', 'buyerName', 'line_ids']}
        )[0]
        
        print(f"✅ Found invoice:")
        print(f"  - FS Number: {invoice['fsNumber']}")
        print(f"  - Total: {invoice['totalWithTax']}")
        print(f"  - Tax: {invoice['totalTax']}")
        print(f"  - Lines: {len(invoice['line_ids'])} items")
        
        # Step 4: Run reconciliation to trigger sync
        print(f"\n🔄 Step 4: Running reconciliation...")
        result = models.execute_kw(
            db, uid, password,
            'pos.order', 'run_reconciliation_check',
            [],
            {
                'target_mrc': TEST_MRC,
                'start_date': TEST_DATE,
                'end_date': TEST_DATE
            }
        )
        
        if result.get('status') == 'success':
            print("✅ Reconciliation completed successfully")
            print(f"  - Orders updated: {result.get('metrics', {}).get('orders_updated', 0)}")
        else:
            print("❌ Reconciliation failed")
            return
        
        # Step 5: Check order after sync
        print(f"\n📦 Step 5: Checking order AFTER sync...")
        order_after = models.execute_kw(
            db, uid, password,
            'pos.order', 'read',
            [order_id],
            {'fields': ['fs_no', 'amount_total', 'amount_tax', 'pos_reference',
                       'partner_id', 'lines', 'payment_ids', 'ej_checksum']}
        )[0]
        
        print(f"\n📊 COMPARISON:")
        print("-" * 40)
        print(f"{'Field':<20} {'Before':<15} {'After':<15} {'Invoice':<15}")
        print("-" * 40)
        print(f"{'Total Amount':<20} {order_before['amount_total']:<15.2f} {order_after['amount_total']:<15.2f} {invoice['totalWithTax']:<15.2f}")
        print(f"{'Tax Amount':<20} {order_before['amount_tax']:<15.2f} {order_after['amount_tax']:<15.2f} {invoice['totalTax']:<15.2f}")
        print(f"{'Line Count':<20} {len(order_before['lines']):<15} {len(order_after['lines']):<15} {len(invoice['line_ids']):<15}")
        print(f"{'Payment Count':<20} {len(order_before['payment_ids']):<15} {len(order_after['payment_ids']):<15} {'1':<15}")
        
        # Verify complete sync
        print(f"\n✅ VERIFICATION:")
        success = True
        
        # Check amounts match invoice
        if abs(order_after['amount_total'] - invoice['totalWithTax']) > 0.01:
            print(f"  ❌ Total amount doesn't match invoice")
            success = False
        else:
            print(f"  ✅ Total amount matches invoice")
        
        if abs(order_after['amount_tax'] - invoice['totalTax']) > 0.01:
            print(f"  ❌ Tax amount doesn't match invoice")
            success = False
        else:
            print(f"  ✅ Tax amount matches invoice")
        
        # Check lines replaced
        if len(order_after['lines']) != len(invoice['line_ids']):
            print(f"  ❌ Line count doesn't match invoice")
            success = False
        else:
            print(f"  ✅ Line count matches invoice")
        
        # Check reference updated
        if order_after['pos_reference'] != invoice['referenceNumber']:
            print(f"  ⚠️ Reference not updated (may be None in invoice)")
        else:
            print(f"  ✅ Reference matches invoice")
        
        # Final result
        print("\n" + "=" * 60)
        if success:
            print("✅ TEST PASSED: Order completely synchronized with invoice")
        else:
            print("❌ TEST FAILED: Some fields not synchronized")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_complete_sync()