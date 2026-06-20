#!/usr/bin/env python3
"""
Test script for POS Fiscal reconciliation with custom dates
Run this with: python3 test_reconciliation_dates.py

This script allows you to:
1. Test reconciliation for specific dates
2. Test for all companies or specific ones
3. See detailed results
"""

import xmlrpc.client
import ssl
from datetime import datetime, timedelta

# Configuration - UPDATE THESE VALUES
url = 'https://baf.demo.zooryatest.et'  # Your Odoo URL
db = 'demo'                              # Your database name
username = 'admin'                       # Your username
password = 'ETTTA@admin'                 # Your password

# Test configuration
TEST_DATES = [
    '2025-05-30',  
   
    # Add more dates as needed
]

def connect_to_odoo():
    """Connect to Odoo and return authenticated user ID and models proxy"""
    print(f"[{datetime.now()}] Connecting to Odoo...")
    
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("❌ Authentication failed!")
        return None, None
    
    print(f"✅ Authenticated as user ID: {uid}")
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    return uid, models

def get_all_companies(models, db, uid, password):
    """Get all companies in the system"""
    print("\n📢 Fetching all companies...")
    
    company_ids = models.execute_kw(
        db, uid, password,
        'res.company', 'search',
        [[]]
    )
    
    companies = models.execute_kw(
        db, uid, password,
        'res.company', 'read',
        [company_ids, ['name']]
    )
    
    print(f"✅ Found {len(companies)} companies:")
    for comp in companies:
        print(f"   - {comp['name']} (ID: {comp['id']})")
    
    return companies

def get_devices_for_company(models, db, uid, password, company_id):
    """Get all POS devices for a specific company"""
    device_ids = models.execute_kw(
        db, uid, password,
        'pos.device', 'search',
        [[['company_id', '=', company_id]]]
    )
    
    if device_ids:
        devices = models.execute_kw(
            db, uid, password,
            'pos.device', 'read',
            [device_ids, ['name', 'mrc']]
        )
        return devices
    return []

def run_reconciliation_for_date(models, db, uid, password, test_date, company_id=None, device_mrc=None):
    """Run reconciliation for a specific date and optionally specific company/device"""
    try:
        if device_mrc:
            # Run for specific device
            print(f"  🔄 Running reconciliation for MRC: {device_mrc}, Date: {test_date}")
            
            result = models.execute_kw(
                db, uid, password,
                'pos.order', 'run_reconciliation_check',
                [],
                {
                    'target_mrc': device_mrc,
                    'start_date': test_date,
                    'end_date': test_date
                }
            )
            return result
        else:
            # Run for all companies using the public method
            print(f"  🔄 Running reconciliation for ALL companies, Date: {test_date}")
            
            # First, we need to temporarily modify the method to accept a date
            # Since we can't modify the server code via XML-RPC, we'll run individual reconciliations
            return None
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return None

def test_all_companies_by_date(models, db, uid, password, test_date):
    """Test reconciliation for all companies on a specific date"""
    print(f"\n📅 Testing reconciliation for date: {test_date}")
    print("=" * 60)
    
    companies = get_all_companies(models, db, uid, password)
    
    total_orders = 0
    total_invoices = 0
    successful_reconciliations = 0
    failed_reconciliations = 0
    
    for company in companies:
        print(f"\n🏢 Processing Company: {company['name']}")
        devices = get_devices_for_company(models, db, uid, password, company['id'])
        
        if not devices:
            print(f"  ⚠️ No devices found for {company['name']}")
            continue
        
        for device in devices:
            print(f"  📱 Device: {device['name']} (MRC: {device['mrc']})")
            
            result = run_reconciliation_for_date(
                models, db, uid, password, 
                test_date, 
                company_id=company['id'],
                device_mrc=device['mrc']
            )
            
            if result and result.get('status') == 'success':
                successful_reconciliations += 1
                orders = result.get('order_count', 0)
                invoices = result.get('invoice_count', 0)
                total_orders += orders
                total_invoices += invoices
                
                print(f"    ✅ Success!")
                print(f"    📊 Orders: {orders}, Invoices: {invoices}")
                print(f"    💰 Order Total: {result.get('order_total', 0):.2f}")
                print(f"    📈 Invoice Total: {result.get('invoice_total', 0):.2f}")
                
                if result.get('metrics'):
                    metrics = result['metrics']
                    print(f"    🔧 Created: {metrics.get('orders_created', 0)}, Updated: {metrics.get('orders_updated', 0)}")
                    print(f"    🔧 Duplicates Fixed: {metrics.get('duplicates_resolved', 0)}")
            else:
                failed_reconciliations += 1
                print(f"    ❌ Failed or no data")
    
    # Summary for this date
    print(f"\n📊 Summary for {test_date}:")
    print(f"  ✅ Successful reconciliations: {successful_reconciliations}")
    print(f"  ❌ Failed reconciliations: {failed_reconciliations}")
    print(f"  📦 Total Orders: {total_orders}")
    print(f"  📄 Total Invoices: {total_invoices}")

def check_daily_reports(models, db, uid, password, test_date):
    """Check if daily reports were created for the test date"""
    print(f"\n📈 Checking daily reports for {test_date}...")
    
    report_ids = models.execute_kw(
        db, uid, password,
        'pos.daily.report', 'search',
        [[['date', '=', test_date]]]
    )
    
    if report_ids:
        reports = models.execute_kw(
            db, uid, password,
            'pos.daily.report', 'read',
            [report_ids, ['fiscal_mrc', 'company_id', 'pos_order_count', 'invoice_count', 
                         'net_order_total', 'net_invoice_total', 'reconciliation_status']]
        )
        
        print(f"✅ Found {len(reports)} daily reports:")
        for report in reports:
            company_name = report['company_id'][1] if report['company_id'] else 'Unknown'
            print(f"\n  📋 Report for MRC: {report['fiscal_mrc']} ({company_name})")
            print(f"    - Orders: {report['pos_order_count']}")
            print(f"    - Invoices: {report['invoice_count']}")
            print(f"    - Order Total: {report['net_order_total']:.2f}")
            print(f"    - Invoice Total: {report['net_invoice_total']:.2f}")
            print(f"    - Status: {report['reconciliation_status']}")
    else:
        print(f"⚠️ No daily reports found for {test_date}")

def main():
    """Main test function"""
    print("=" * 60)
    print("POS FISCAL RECONCILIATION DATE TEST")
    print("=" * 60)
    
    uid, models = connect_to_odoo()
    if not uid:
        return
    
    # Test each date
    for test_date in TEST_DATES:
        test_all_companies_by_date(models, db, uid, password, test_date)
        check_daily_reports(models, db, uid, password, test_date)
        print("\n" + "=" * 60)
    
    print("\n✅ All tests completed!")
    
    # Optional: Show overall summary
    print("\n📊 OVERALL SUMMARY")
    print("=" * 60)
    print(f"Tested {len(TEST_DATES)} dates")
    print(f"Dates tested: {', '.join(TEST_DATES)}")

if __name__ == '__main__':
    # You can also run with command line arguments
    import sys
    
    if len(sys.argv) > 1:
        # Allow passing dates as command line arguments
        # Usage: python3 test_reconciliation_dates.py 2025-01-15 2025-01-16
        TEST_DATES = sys.argv[1:]
        print(f"Testing dates from command line: {TEST_DATES}")
    
    main()