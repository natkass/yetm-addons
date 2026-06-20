#!/usr/bin/env python3
"""
Test Script for POS Invoice Auto-Reconciliation
This script creates a POS invoice and tests the automatic reconciliation process
"""

import xmlrpc.client
from datetime import datetime, timedelta
import time
import sys

# Odoo connection parameters - Update these with your actual values
url = 'https://baf.demo.zooryatest.et'  # Your Odoo URL
db = 'demo'                              # Your database name
username = 'admin'                       # Your username
password = 'ETTTA@admin'                 # Your password

def connect_odoo():
    """Establish connection to Odoo"""
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    
    if not uid:
        print("❌ Failed to authenticate with Odoo")
        sys.exit(1)
    
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    print(f"✅ Connected to Odoo database '{DB}' as user '{USERNAME}' (UID: {uid})")
    return models, uid

def execute(models, uid, model, method, *args):
    """Execute Odoo method with error handling"""
    try:
        return models.execute_kw(DB, uid, PASSWORD, model, method, *args)
    except Exception as e:
        print(f"❌ Error executing {model}.{method}: {str(e)}")
        return None

def test_invoice_reconciliation(models, uid):
    """Main test function"""
    print("\n" + "="*60)
    print("🧪 TESTING POS INVOICE AUTO-RECONCILIATION")
    print("="*60)
    
    # 1. Get or create test device
    print("\n📱 Step 1: Setting up test device...")
    devices = execute(models, uid, 'pos.device', 'search_read', 
                     [('mrc', '=', 'URB0000380')], 
                     {'fields': ['id', 'name', 'mrc', 'company_id']})
    
    if devices:
        device = devices[0]
        print(f"   Found device: {device['name']} (MRC: {device['mrc']})")
    else:
        # Create test device
        device_id = execute(models, uid, 'pos.device', 'create', [{
            'name': 'Test Device',
            'mrc': 'URB0000380',
            'company_id': 1,  # Default company
        }])
        device = {'id': device_id, 'mrc': 'URB0000380'}
        print(f"   Created test device with MRC: {device['mrc']}")
    
    # 2. Generate unique FS number for testing
    import random
    test_fs_number = random.randint(900000, 999999)
    test_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n📝 Step 2: Creating test invoice...")
    print(f"   FS Number: {test_fs_number}")
    print(f"   Date: {test_date}")
    print(f"   Amount: 1500.00")
    
    # 3. Check if order already exists
    existing_orders = execute(models, uid, 'pos.order', 'search_read',
                             [('fs_no', 'in', [str(test_fs_number), f"{test_fs_number:08d}"])],
                             {'fields': ['id', 'fs_no', 'amount_total', 'state']})
    
    if existing_orders:
        print(f"   ⚠️  Found existing order with FS {test_fs_number}, cancelling it...")
        for order in existing_orders:
            execute(models, uid, 'pos.order', 'write', 
                   [[order['id']], {'state': 'cancel'}])
    
    # 4. Create invoice lines
    invoice_lines = []
    products = [
        {'name': 'Pizza Margherita', 'quantity': 2, 'price': 500.00, 'pluCode': 'PLU001'},
        {'name': 'Coca Cola', 'quantity': 3, 'price': 100.00, 'pluCode': 'PLU002'},
        {'name': 'Garlic Bread', 'quantity': 1, 'price': 200.00, 'pluCode': 'PLU003'},
    ]
    
    for idx, product in enumerate(products):
        line_total = product['quantity'] * product['price']
        invoice_lines.append((0, 0, {
            'lineIndex': str(idx + 1),
            'pluCode': product['pluCode'],
            'itemName': product['name'],
            'quantity': product['quantity'],
            'price': product['price'],
            'lineTotal': line_total,
            'lineTotalWithTax': line_total * 1.15,  # 15% tax
            'taxRate': 15.0,
            'taxAmount': line_total * 0.15,
        }))
    
    # 5. Create POS Invoice
    invoice_vals = {
        'fsNumber': test_fs_number,
        'device_id': device['id'],
        'date': test_date,
        'referenceNumber': f"REF-{test_fs_number}",
        'paymentType': 'Cash',
        'buyerName': 'Test Customer',
        'cashierName': 'Test Cashier',
        'totalWithoutTax': 1300.00,
        'totalTax': 195.00,
        'totalWithTax': 1495.00,
        'totalPaid': 1500.00,
        'change': 5.00,
        'line_ids': invoice_lines,
    }
    
    invoice_id = execute(models, uid, 'pos.invoice', 'create', [invoice_vals])
    
    if not invoice_id:
        print("❌ Failed to create invoice")
        return False
    
    print(f"   ✅ Created invoice ID: {invoice_id}")
    
    # 6. Wait for reconciliation to trigger
    print(f"\n⏳ Step 3: Waiting for auto-reconciliation (10 seconds)...")
    for i in range(10, 0, -1):
        print(f"   {i} seconds remaining...", end='\r')
        time.sleep(1)
    
    print("\n\n🔍 Step 4: Checking reconciliation status...")
    
    # Check invoice reconciliation status
    invoice = execute(models, uid, 'pos.invoice', 'read', 
                     [invoice_id], 
                     ['reconciliation_status', 'reconciliation_job_uuid'])[0]
    
    print(f"   Invoice reconciliation status: {invoice.get('reconciliation_status', 'unknown')}")
    if invoice.get('reconciliation_job_uuid'):
        print(f"   Job UUID: {invoice['reconciliation_job_uuid']}")
    
    # Wait a bit more for processing
    print("\n⏳ Waiting additional 5 seconds for processing...")
    time.sleep(5)
    
    # 7. Check if POS Order was created
    print("\n📦 Step 5: Checking for created POS Order...")
    
    # Search for orders with our FS number
    fs_variations = [
        str(test_fs_number),
        f"{test_fs_number:08d}",
        str(test_fs_number).lstrip('0'),
    ]
    
    orders = execute(models, uid, 'pos.order', 'search_read',
                    [('fs_no', 'in', fs_variations),
                     ('fiscal_mrc', '=', device['mrc']),
                     ('state', '!=', 'cancel')],
                    {'fields': ['id', 'fs_no', 'amount_total', 'state', 'date_order', 
                              'pos_reference', 'fiscal_mrc']})
    
    if orders:
        print(f"   ✅ SUCCESS! Found {len(orders)} order(s):")
        for order in orders:
            print(f"      - Order ID: {order['id']}")
            print(f"        FS Number: {order['fs_no']}")
            print(f"        Amount: {order['amount_total']:.2f}")
            print(f"        State: {order['state']}")
            print(f"        MRC: {order['fiscal_mrc']}")
            print(f"        Reference: {order.get('pos_reference', 'N/A')}")
    else:
        print("   ❌ No POS Order found! Checking logs...")
        
        # Check daily report for insights
        reports = execute(models, uid, 'pos.daily.report', 'search_read',
                         [('date', '=', test_date),
                          ('fiscal_mrc', '=', device['mrc'])],
                         {'fields': ['invoice_count', 'pos_order_count', 'recreated_orders', 
                                   'updated_orders', 'unmatched_fs_count']})
        
        if reports:
            report = reports[0]
            print("\n   📊 Daily Report Stats:")
            print(f"      Invoices: {report['invoice_count']}")
            print(f"      Orders: {report['pos_order_count']}")
            print(f"      Recreated: {report['recreated_orders']}")
            print(f"      Updated: {report['updated_orders']}")
            print(f"      Unmatched: {report['unmatched_fs_count']}")
    
    # 8. Check change logs
    print("\n📜 Step 6: Checking change logs...")
    logs = execute(models, uid, 'pos.change.log', 'search_read',
                  [('fs_no', 'in', [str(test_fs_number), f"{test_fs_number:08d}"]),
                   ('date', '>=', datetime.now().strftime('%Y-%m-%d 00:00:00'))],
                  {'fields': ['date', 'change_type', 'old_value', 'new_value', 'pos_order_id'],
                   'order': 'date desc'})
    
    if logs:
        print(f"   Found {len(logs)} log entries:")
        for log in logs:
            print(f"      - {log['date']}: {log['change_type']}")
            print(f"        Old: {log.get('old_value', 'N/A')}")
            print(f"        New: {log.get('new_value', 'N/A')}")
            if log.get('pos_order_id'):
                print(f"        Order ID: {log['pos_order_id'][0]}")
    else:
        print("   No change logs found")
    
    # 9. Manual reconciliation trigger (fallback test)
    if not orders:
        print("\n🔧 Step 7: Manually triggering reconciliation...")
        result = execute(models, uid, 'pos.order', 'run_reconciliation_check',
                        [device['mrc'], test_date, test_date])
        
        if result:
            print(f"   Reconciliation result: {result.get('status', 'unknown')}")
            if result.get('metrics'):
                print(f"   Orders created: {result['metrics'].get('orders_created', 0)}")
                print(f"   Orders updated: {result['metrics'].get('orders_updated', 0)}")
        
        # Check again for orders
        orders = execute(models, uid, 'pos.order', 'search_read',
                        [('fs_no', 'in', fs_variations),
                         ('fiscal_mrc', '=', device['mrc']),
                         ('state', '!=', 'cancel')],
                        {'fields': ['id', 'fs_no', 'amount_total', 'state']})
        
        if orders:
            print(f"\n   ✅ Order created after manual reconciliation!")
            for order in orders:
                print(f"      Order ID: {order['id']}, FS: {order['fs_no']}, Amount: {order['amount_total']:.2f}")
        else:
            print("\n   ❌ Still no order created after manual reconciliation")
    
    print("\n" + "="*60)
    print("🏁 TEST COMPLETED")
    print("="*60)
    
    return bool(orders)

def main():
    """Main execution"""
    try:
        models, uid = connect_odoo()
        success = test_invoice_reconciliation(models, uid)
        
        if success:
            print("\n✅ TEST PASSED: Invoice reconciliation is working correctly!")
            sys.exit(0)
        else:
            print("\n❌ TEST FAILED: Invoice reconciliation did not create POS order")
            print("\n🔍 Troubleshooting suggestions:")
            print("   1. Check Odoo logs for error messages")
            print("   2. Verify queue_job module is installed and running")
            print("   3. Check if there are permission issues")
            print("   4. Ensure POS sessions exist for the date")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()