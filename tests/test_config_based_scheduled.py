#!/usr/bin/env python3
"""
Test script to verify configuration-based scheduled payments work correctly.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date
from decimal import Decimal
from family_mobile_ledger.scheduled import (
    update_all_scheduled, _load_config, enrique_payment, daniel_payment, 
    seth_payment, wsj_charge
)

def test_config_loading():
    """Test that configuration loads correctly"""
    print("🧪 Testing configuration loading...")
    
    try:
        config = _load_config()
        
        # Verify config structure
        assert 'monthly_payments' in config, "Config should have monthly_payments section"
        assert 'periodic_charges' in config, "Config should have periodic_charges section"
        assert 'bill_triggered_payments' in config, "Config should have bill_triggered_payments section"
        assert 'settings' in config, "Config should have settings section"
        assert 'metadata' in config, "Config should have metadata section"
        
        # Verify specific payment configs
        assert 'enrique' in config['monthly_payments'], "Should have Enrique config"
        assert 'daniel' in config['monthly_payments'], "Should have Daniel config"
        assert 'seth' in config['monthly_payments'], "Should have Seth config"
        assert 'wsj' in config['periodic_charges'], "Should have WSJ config"
        
        # Verify Enrique config details
        enrique_config = config['monthly_payments']['enrique']
        assert enrique_config['amount'] == -105.59, f"Enrique amount should be -105.59, got {enrique_config['amount']}"
        assert enrique_config['day_of_month'] == 6, f"Enrique day should be 6, got {enrique_config['day_of_month']}"
        assert enrique_config['family'] == "RE", f"Enrique family should be RE, got {enrique_config['family']}"
        
        # Verify WSJ config details
        wsj_config = config['periodic_charges']['wsj']
        assert wsj_config['amount'] == 70.76, f"WSJ amount should be 70.76, got {wsj_config['amount']}"
        assert wsj_config['interval_days'] == 28, f"WSJ interval should be 28 days, got {wsj_config['interval_days']}"
        assert wsj_config['auto_jonah_payment']['enabled'] == True, "WSJ auto Jonah payment should be enabled"
        
        print(f"✅ Configuration loaded successfully (version {config['metadata']['config_version']})")
        return True
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False

def test_config_based_payments():
    """Test that config-based payments generate correctly"""
    print("\n🧪 Testing config-based payment generation...")
    
    try:
        # Test individual payment functions
        empty_ledger = []
        
        # Test Enrique payments
        enrique_ledger = enrique_payment(empty_ledger)
        enrique_entries = [r for r in enrique_ledger if 'Enrique' in r.description]
        assert len(enrique_entries) > 0, "Should generate Enrique payments"
        assert enrique_entries[0].amount == Decimal('-105.59'), "Enrique amount should match config"
        assert enrique_entries[0].re == Decimal('-105.59'), "Enrique should be assigned to RE family"
        print(f"✅ Enrique: {len(enrique_entries)} payments generated")
        
        # Test Daniel payments
        daniel_ledger = daniel_payment(empty_ledger)
        daniel_entries = [r for r in daniel_ledger if 'Daniel' in r.description]
        assert len(daniel_entries) > 0, "Should generate Daniel payments"
        assert daniel_entries[0].amount == Decimal('-69.73'), "Daniel amount should match config"
        assert daniel_entries[0].dj == Decimal('-69.73'), "Daniel should be assigned to DJ family"
        print(f"✅ Daniel: {len(daniel_entries)} payments generated")
        
        # Test Seth payments
        seth_ledger = seth_payment(empty_ledger)
        seth_entries = [r for r in seth_ledger if 'Seth' in r.description]
        assert len(seth_entries) > 0, "Should generate Seth payments"
        assert seth_entries[0].amount == Decimal('-77.00'), "Seth amount should match config"
        assert seth_entries[0].ks == Decimal('-77.00'), "Seth should be assigned to KS family"
        print(f"✅ Seth: {len(seth_entries)} payments generated")
        
        # Test WSJ charges
        wsj_ledger = wsj_charge(empty_ledger)
        wsj_charges = [r for r in wsj_ledger if 'WSJ' in r.description and r.category == 'misc']
        wsj_payments = [r for r in wsj_ledger if 'jonah' in r.description.lower() and r.category == 'payment']
        
        assert len(wsj_charges) > 0, "Should generate WSJ charges"
        assert len(wsj_payments) > 0, "Should generate WSJ Jonah payments"
        assert len(wsj_charges) == len(wsj_payments), "Should have equal WSJ charges and Jonah payments"
        
        assert wsj_charges[0].amount == Decimal('70.76'), "WSJ amount should match config"
        assert wsj_charges[0].jj == Decimal('23.59'), "WSJ JJ cost should match config"
        assert wsj_payments[0].amount == Decimal('-23.59'), "Jonah payment should match config"
        
        print(f"✅ WSJ: {len(wsj_charges)} charges and {len(wsj_payments)} Jonah payments generated")
        
        return True
        
    except Exception as e:
        print(f"❌ Config-based payment generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config_dates():
    """Test that config dates are parsed correctly"""
    print("\n🧪 Testing configuration date parsing...")
    
    try:
        config = _load_config()
        
        # Test monthly payment dates
        enrique_start = config['monthly_payments']['enrique']['start_date']
        daniel_start = config['monthly_payments']['daniel']['start_date']
        seth_start = config['monthly_payments']['seth']['start_date']
        
        print(f"✅ Start dates: Enrique({enrique_start}), Daniel({daniel_start}), Seth({seth_start})")
        
        # Test WSJ start date
        wsj_start = config['periodic_charges']['wsj']['start_date']
        print(f"✅ WSJ start date: {wsj_start}")
        
        # Generate payments and verify dates are reasonable
        empty_ledger = []
        updated_ledger = update_all_scheduled(empty_ledger)
        
        # Check that payments start from appropriate dates
        enrique_entries = [r for r in updated_ledger if 'Enrique' in r.description]
        if enrique_entries:
            earliest_enrique = min(r.date for r in enrique_entries)
            assert earliest_enrique >= date(2025, 1, 6), f"Earliest Enrique payment should be >= 2025-01-06, got {earliest_enrique}"
        
        seth_entries = [r for r in updated_ledger if 'Seth' in r.description]
        if seth_entries:
            earliest_seth = min(r.date for r in seth_entries)
            assert earliest_seth >= date(2024, 1, 15), f"Earliest Seth payment should be >= 2024-01-15, got {earliest_seth}"
        
        wsj_entries = [r for r in updated_ledger if 'WSJ' in r.description and r.category == 'misc']
        if wsj_entries:
            earliest_wsj = min(r.date for r in wsj_entries)
            assert earliest_wsj >= date(2024, 9, 15), f"Earliest WSJ charge should be >= 2024-09-15, got {earliest_wsj}"
        
        print("✅ All payment dates are within expected ranges")
        return True
        
    except Exception as e:
        print(f"❌ Date parsing test failed: {e}")
        return False

def test_comprehensive_config_system():
    """Test the complete configuration-based system"""
    print("\n🧪 Testing comprehensive config-based system...")
    
    try:
        empty_ledger = []
        updated_ledger = update_all_scheduled(empty_ledger)
        
        print(f"✅ Generated {len(updated_ledger)} total scheduled entries")
        
        # Categorize and count entries
        enrique_payments = [r for r in updated_ledger if 'Enrique' in r.description and r.category == 'payment']
        daniel_payments = [r for r in updated_ledger if 'Daniel' in r.description and r.category == 'payment']
        seth_payments = [r for r in updated_ledger if 'Seth' in r.description and r.category == 'payment']
        wsj_charges = [r for r in updated_ledger if 'WSJ' in r.description and r.category == 'misc']
        jonah_wsj_payments = [r for r in updated_ledger if 'jonah' in r.description.lower() and r.category == 'payment']
        
        print(f"✅ Entry breakdown:")
        print(f"   - Enrique payments: {len(enrique_payments)}")
        print(f"   - Daniel payments: {len(daniel_payments)}")
        print(f"   - Seth payments: {len(seth_payments)}")
        print(f"   - WSJ charges: {len(wsj_charges)}")
        print(f"   - Jonah WSJ payments: {len(jonah_wsj_payments)}")
        
        # Verify all expected types are present
        assert len(enrique_payments) > 0, "Should have Enrique payments"
        assert len(daniel_payments) > 0, "Should have Daniel payments"
        assert len(seth_payments) > 0, "Should have Seth payments"
        assert len(wsj_charges) > 0, "Should have WSJ charges"
        assert len(jonah_wsj_payments) > 0, "Should have Jonah WSJ payments"
        
        # Verify WSJ-Jonah pairing
        assert len(wsj_charges) == len(jonah_wsj_payments), "WSJ charges should match Jonah payments"
        
        # Verify amounts match configuration
        config = _load_config()
        
        if enrique_payments:
            expected_amount = Decimal(str(config['monthly_payments']['enrique']['amount']))
            assert enrique_payments[0].amount == expected_amount, f"Enrique amount mismatch"
        
        if wsj_charges:
            expected_amount = Decimal(str(config['periodic_charges']['wsj']['amount']))
            assert wsj_charges[0].amount == expected_amount, f"WSJ amount mismatch"
        
        if jonah_wsj_payments:
            expected_amount = Decimal(str(config['periodic_charges']['wsj']['auto_jonah_payment']['amount']))
            assert jonah_wsj_payments[0].amount == expected_amount, f"Jonah WSJ payment amount mismatch"
        
        print("✅ All amounts match configuration")
        print("✅ Configuration-based system working perfectly!")
        
        return True
        
    except Exception as e:
        print(f"❌ Comprehensive system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    try:
        test1 = test_config_loading()
        test2 = test_config_based_payments()
        test3 = test_config_dates()
        test4 = test_comprehensive_config_system()
        
        if all([test1, test2, test3, test4]):
            print("\n🏆 All configuration-based scheduled payment tests passed!")
            print("🎉 Configuration system is working perfectly!")
            print("📋 Benefits:")
            print("   ✅ Easy to modify payment amounts and dates")
            print("   ✅ Clear configuration structure")
            print("   ✅ Historical tracking of changes")
            print("   ✅ Enable/disable individual payments")
        else:
            print("\n💥 Some tests failed!")
            exit(1)
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)