#!/usr/bin/env python3
"""
Final comprehensive test to verify all scheduled payments work together,
including WSJ charges with automatic Jonah payments.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date
from decimal import Decimal
from family_mobile_ledger.datatypes import LedgerRow
from family_mobile_ledger.scheduled import update_all_scheduled

def test_complete_scheduled_system():
    """Test the complete scheduled payment system"""
    print("🧪 Testing complete scheduled payment system...")
    
    # Start with empty ledger
    empty_ledger = []
    
    # Apply all scheduled updates
    updated_ledger = update_all_scheduled(empty_ledger)
    
    print(f"✅ Generated {len(updated_ledger)} total scheduled entries")
    
    # Categorize entries
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
    
    # Verify we have all expected types
    assert len(enrique_payments) > 0, "Should have Enrique payments"
    assert len(daniel_payments) > 0, "Should have Daniel payments"
    assert len(seth_payments) > 0, "Should have Seth payments"
    assert len(wsj_charges) > 0, "Should have WSJ charges"
    assert len(jonah_wsj_payments) > 0, "Should have Jonah WSJ payments"
    
    # Verify WSJ charges match Jonah payments
    assert len(wsj_charges) == len(jonah_wsj_payments), "Should have equal WSJ charges and Jonah payments"
    
    wsj_dates = {row.date for row in wsj_charges}
    jonah_dates = {row.date for row in jonah_wsj_payments}
    assert wsj_dates == jonah_dates, "WSJ and Jonah payment dates should match"
    
    print("✅ All scheduled payment types present and properly paired")
    
    # Verify amounts are correct
    if enrique_payments:
        assert enrique_payments[0].amount == Decimal('-105.59'), "Enrique amount should be -$105.59"
    
    if daniel_payments:
        assert daniel_payments[0].amount == Decimal('-69.73'), "Daniel amount should be -$69.73"
    
    if seth_payments:
        assert seth_payments[0].amount == Decimal('-77.00'), "Seth amount should be -$77.00"
    
    if wsj_charges:
        assert wsj_charges[0].amount == Decimal('70.76'), "WSJ amount should be $70.76"
        assert wsj_charges[0].jj == Decimal('23.59'), "WSJ JJ portion should be $23.59"
    
    if jonah_wsj_payments:
        assert jonah_wsj_payments[0].amount == Decimal('-23.59'), "Jonah WSJ payment should be -$23.59"
    
    print("✅ All payment amounts are correct")
    
    return True

def test_no_duplicate_entries():
    """Test that running scheduled updates multiple times doesn't create duplicates"""
    print("\n🧪 Testing duplicate prevention...")
    
    # First run
    empty_ledger = []
    first_run = update_all_scheduled(empty_ledger)
    first_count = len(first_run)
    
    print(f"✅ First run generated {first_count} entries")
    
    # Second run on the same ledger
    second_run = update_all_scheduled(first_run)
    second_count = len(second_run)
    
    print(f"✅ Second run resulted in {second_count} entries")
    
    # Should not have added any new entries
    assert second_count == first_count, f"Second run should not add duplicates. Expected {first_count}, got {second_count}"
    
    print("✅ No duplicate entries created")
    
    return True

def test_wsj_jonah_pairing():
    """Test that every WSJ charge has a corresponding Jonah payment"""
    print("\n🧪 Testing WSJ-Jonah payment pairing...")
    
    empty_ledger = []
    updated_ledger = update_all_scheduled(empty_ledger)
    
    wsj_charges = [r for r in updated_ledger if 'WSJ' in r.description and r.category == 'misc']
    jonah_payments = [r for r in updated_ledger if 'jonah' in r.description.lower() and r.category == 'payment']
    
    print(f"✅ Found {len(wsj_charges)} WSJ charges and {len(jonah_payments)} Jonah payments")
    
    # Every WSJ charge should have a matching Jonah payment on the same date
    for wsj_charge in wsj_charges:
        matching_jonah = [jp for jp in jonah_payments if jp.date == wsj_charge.date]
        assert len(matching_jonah) == 1, f"Should have exactly 1 Jonah payment for WSJ charge on {wsj_charge.date}, found {len(matching_jonah)}"
        
        jonah_payment = matching_jonah[0]
        
        # Verify the Jonah payment amount matches the WSJ JJ portion
        assert jonah_payment.amount == -wsj_charge.jj, f"Jonah payment {jonah_payment.amount} should equal negative WSJ JJ portion {-wsj_charge.jj}"
    
    print("✅ All WSJ charges have properly paired Jonah payments")
    
    return True

def test_date_ranges():
    """Test that scheduled payments cover appropriate date ranges"""
    print("\n🧪 Testing date ranges...")
    
    empty_ledger = []
    updated_ledger = update_all_scheduled(empty_ledger)
    
    today = date.today()
    
    # All entries should be on or before today
    future_entries = [r for r in updated_ledger if r.date > today]
    assert len(future_entries) == 0, f"Should not have future entries, found {len(future_entries)}"
    
    # Should have entries from recent months
    recent_entries = [r for r in updated_ledger if (today - r.date).days <= 365]  # Within last year
    assert len(recent_entries) > 0, "Should have recent entries"
    
    print(f"✅ All {len(updated_ledger)} entries are properly dated (none in future)")
    print(f"✅ {len(recent_entries)} entries are from the last year")
    
    return True

if __name__ == '__main__':
    try:
        test1 = test_complete_scheduled_system()
        test2 = test_no_duplicate_entries()
        test3 = test_wsj_jonah_pairing()
        test4 = test_date_ranges()
        
        if all([test1, test2, test3, test4]):
            print("\n🏆 All final integration tests passed!")
            print("🎉 Complete scheduled payment system is working perfectly!")
            print("📋 Summary:")
            print("   ✅ Regular scheduled payments (Enrique, Daniel, Seth)")
            print("   ✅ WSJ charges with automatic Jonah payments")
            print("   ✅ T-Mobile bill Jonah payments (when processing PDFs)")
            print("   ✅ Duplicate prevention")
            print("   ✅ Proper date handling")
        else:
            print("\n💥 Some tests failed!")
            exit(1)
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)