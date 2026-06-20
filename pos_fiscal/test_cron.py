#!/usr/bin/env python3
"""
Test script for POS Fiscal daily reconciliation cron job
Run this with: python3 test_cron.py
"""

import xmlrpc.client
import ssl
from datetime import datetime

# Configuration - UPDATE THESE VALUES
url = 'https://baf.demo.zooryatest.et'  # Your Odoo URL
db = 'demo'       # Your database name
username = 'admin'               # Your username
password = 'ETTTA@admin'               # Your password

def test_cron_job():
    """Test the daily reconciliation cron job"""
    
    print(f"[{datetime.now()}] Connecting to Odoo...")
    
    # Connect to Odoo
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("❌ Authentication failed!")
        return
    
    print(f"✅ Authenticated as user ID: {uid}")
    
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    try:
        # Test 1: Check if cron job exists
        print("\n📋 Checking cron job...")
        cron_ids = models.execute_kw(
            db, uid, password,
            'ir.cron', 'search',
            [[['name', '=', 'Daily POS Reconciliation']]]
        )
        
        if cron_ids:
            print(f"✅ Found cron job ID: {cron_ids[0]}")
            
            # Get cron details
            cron_data = models.execute_kw(
                db, uid, password,
                'ir.cron', 'read',
                [cron_ids[0], ['name', 'active', 'nextcall', 'interval_number', 'interval_type']]
            )
            print(f"📊 Cron details: {cron_data}")
            
            # Test 2: Run the reconciliation manually
            print("\n🚀 Running reconciliation manually...")
            result = models.execute_kw(
                db, uid, password,
                'pos.order', 'queue_daily_reconciliation_all_companies',
                []
            )
            print(f"✅ Reconciliation started: {result}")
            
            # Test 3: Check for any daily reports created
            print("\n📈 Checking daily reports...")
            report_ids = models.execute_kw(
                db, uid, password,
                'pos.daily.report', 'search',
                [[['date', '=', datetime.now().strftime('%Y-%m-%d')]]]
            )
            
            if report_ids:
                print(f"✅ Found {len(report_ids)} daily report(s) for today")
                
                # Get report details
                reports = models.execute_kw(
                    db, uid, password,
                    'pos.daily.report', 'read',
                    [report_ids, ['fiscal_mrc', 'pos_order_count', 'invoice_count', 'reconciliation_status']]
                )
                
                for report in reports:
                    print(f"  - MRC: {report['fiscal_mrc']}, Orders: {report['pos_order_count']}, Status: {report['reconciliation_status']}")
            else:
                print("ℹ️ No daily reports found for today")
                
        else:
            print("❌ Cron job 'Daily POS Reconciliation' not found!")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def test_manual_reconciliation():
    """Test manual reconciliation for a specific MRC"""
    
    print(f"\n[{datetime.now()}] Testing manual reconciliation...")
    
    # Connect to Odoo
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("❌ Authentication failed!")
        return
    
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    try:
        # Get first available device
        device_ids = models.execute_kw(
            db, uid, password,
            'pos.device', 'search',
            [[]],  # Get all devices, no filter on active field
            {'limit': 1}
        )
        
        if device_ids:
            device = models.execute_kw(
                db, uid, password,
                'pos.device', 'read',
                [device_ids[0], ['name', 'mrc']]
            )
            
            print(f"🎯 Testing with device: {device['name']} (MRC: {device['mrc']})")
            
            # Run reconciliation
            result = models.execute_kw(
                db, uid, password,
                'pos.order', 'run_reconciliation_check',
                [],
                {
                    'target_mrc': device['mrc'],
                    'start_date': datetime.now().strftime('%Y-%m-%d'),
                    'end_date': datetime.now().strftime('%Y-%m-%d')
                }
            )
            
            print(f"✅ Reconciliation result: {result}")
        else:
            print("⚠️ No active devices found")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    print("=" * 60)
    print("POS FISCAL CRON JOB TEST")
    print("=" * 60)
    
    # Test cron job
    test_cron_job()
    
    # Test manual reconciliation
    test_manual_reconciliation()
    
    print("\n✅ Test completed!")