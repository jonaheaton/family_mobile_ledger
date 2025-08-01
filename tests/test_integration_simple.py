#!/usr/bin/env python3
"""
Simple integration test for the scheduled payment functionality without CLI dependencies.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date
from decimal import Decimal
from family_mobile_ledger.datatypes import LedgerRow
from family_mobile_ledger.scheduled import (
    update_all_scheduled, jonah_payment_for_bill, add_jonah_payment_if_missing
)

def test_scheduled_integration():
    """Test that all scheduled payments work together"""
    print("🧪 Testing scheduled payment integration...")
    
    # Start with empty ledger
    empty_ledger = []
    
    # Apply all scheduled updates
    updated_ledger = update_all_scheduled(empty_ledger)
    
    print(f"✅ Generated {len(updated_ledger)} scheduled entries")
    
    # Verify we have all expected payment types
    enrique_payments = [r for r in updated_ledger if 'Enrique' in r.description]
    daniel_payments = [r for r in updated_ledger if 'Daniel' in r.description]  
    seth_payments = [r for r in updated_ledger if 'Seth' in r.description]
    wsj_charges = [r for r in updated_ledger if 'WSJ' in r.description]
    
    print(f"✅ Payment breakdown:")
    print(f"   - Enrique: {len(enrique_payments)} payments")
    print(f"   - Daniel: {len(daniel_payments)} payments")
    print(f"   - Seth: {len(seth_payments)} payments")
    print(f"   - WSJ: {len(wsj_charges)} charges")
    
    assert len(enrique_payments) > 0, "Should have Enrique payments"
    assert len(daniel_payments) > 0, "Should have Daniel payments"
    assert len(seth_payments) > 0, "Should have Seth payments"
    assert len(wsj_charges) > 0, "Should have WSJ charges"
    
    return True

def test_jonah_payment_workflow():
    """Test the complete Jonah payment workflow"""
    print("\n💰 Testing Jonah payment workflow...")
    
    # Create a sample T-Mobile bill
    due_date = date(2025, 6, 24)
    
    bill_rows = [
        LedgerRow(
            description="10 voice lines",
            date=due_date,
            amount=Decimal('280.00'),
            category='service',
            shares_jj=2, shares_ks=6, shares_dj=1, shares_re=2,
            shares_total=11,
            jj=Decimal('50.91'),
            ks=Decimal('152.73'),
            dj=Decimal('25.45'),
            re=Decimal('50.91')
        ),
        LedgerRow(
            description="jonah iphone",
            date=due_date,
            amount=Decimal('33.34'),
            category='equipment',
            shares_jj=1, shares_ks=None, shares_dj=None, shares_re=None,
            shares_total=1,
            jj=Decimal('33.34'),
            ks=Decimal('0.00'),
            dj=Decimal('0.00'),
            re=Decimal('0.00')
        ),
        LedgerRow(
            description="netflix",
            date=due_date,
            amount=Decimal('18.00'),
            category='service',
            shares_jj=2, shares_ks=2, shares_dj=2, shares_re=2,
            shares_total=8,
            jj=Decimal('4.50'),
            ks=Decimal('4.50'),
            dj=Decimal('4.50'),
            re=Decimal('4.50')
        )
    ]
    
    print(f"✅ Created sample T-Mobile bill with {len(bill_rows)} entries")
    
    # Test 1: Calculate Jonah payment
    jonah_payment = jonah_payment_for_bill(bill_rows, due_date)
    
    assert jonah_payment is not None, "Jonah payment should be calculated"
    
    expected_jj_total = Decimal('50.91') + Decimal('33.34') + Decimal('4.50')  # 88.75
    expected_payment = -expected_jj_total
    
    assert jonah_payment.amount == expected_payment, f"Expected {expected_payment}, got {jonah_payment.amount}"
    print(f"✅ Jonah payment calculated correctly: {expected_payment}")
    
    # Test 2: Add to ledger
    existing_ledger = bill_rows.copy()  # Start with the bill entries
    
    updated_ledger = add_jonah_payment_if_missing(existing_ledger, bill_rows, due_date)
    
    assert len(updated_ledger) == len(existing_ledger) + 1, "Should have added Jonah payment"
    
    jonah_entries = [r for r in updated_ledger if 'jonah' in r.description.lower() and r.category == 'payment']
    assert len(jonah_entries) == 1, "Should have exactly one Jonah payment"
    
    print(f"✅ Jonah payment added to ledger: {jonah_entries[0].amount}")
    
    # Test 3: Duplicate prevention
    updated_again = add_jonah_payment_if_missing(updated_ledger, bill_rows, due_date)
    
    assert len(updated_again) == len(updated_ledger), "Should not add duplicate"
    
    jonah_entries_again = [r for r in updated_again if 'jonah' in r.description.lower() and r.category == 'payment']
    assert len(jonah_entries_again) == 1, "Should still have exactly one Jonah payment"
    
    print("✅ Duplicate prevention works correctly")
    
    return True

def test_comprehensive_workflow():
    """Test the complete workflow with both scheduled payments and Jonah payments"""
    print("\n🎯 Testing comprehensive workflow...")
    
    # Step 1: Start with scheduled payments
    ledger = update_all_scheduled([])
    initial_count = len(ledger)
    print(f"✅ Added {initial_count} scheduled entries")
    
    # Step 2: Process a T-Mobile bill
    due_date = date(2025, 6, 24)
    
    bill_rows = [
        LedgerRow(
            description="voice lines",
            date=due_date,
            amount=Decimal('100.00'),
            category='service',
            shares_jj=1, shares_ks=1, shares_dj=1, shares_re=1,
            shares_total=4,
            jj=Decimal('25.00'),
            ks=Decimal('25.00'),
            dj=Decimal('25.00'),
            re=Decimal('25.00')
        )
    ]
    
    # Add bill entries to ledger
    ledger.extend(bill_rows)
    
    # Add Jonah payment
    ledger = add_jonah_payment_if_missing(ledger, bill_rows, due_date)
    
    final_count = len(ledger)
    print(f"✅ Final ledger has {final_count} entries ({final_count - initial_count - 1} bill + 1 Jonah payment)")
    
    # Verify we have both scheduled and Jonah payments
    scheduled_payments = [r for r in ledger if r.category == 'payment' and 'jonah' not in r.description.lower()]
    jonah_payments = [r for r in ledger if r.category == 'payment' and 'jonah' in r.description.lower()]
    bill_entries = [r for r in ledger if r.category != 'payment']
    
    print(f"✅ Ledger breakdown:")
    print(f"   - Scheduled payments: {len(scheduled_payments)}")
    print(f"   - Jonah payments: {len(jonah_payments)}")
    print(f"   - Bill/expense entries: {len(bill_entries)}")
    
    assert len(scheduled_payments) > 0, "Should have scheduled payments"
    assert len(jonah_payments) == 1, "Should have exactly one Jonah payment"
    assert len(bill_entries) > 0, "Should have bill entries"
    
    return True

if __name__ == '__main__':
    try:
        test1 = test_scheduled_integration()
        test2 = test_jonah_payment_workflow()
        test3 = test_comprehensive_workflow()
        
        if test1 and test2 and test3:
            print("\n🏆 All integration tests passed!")
            print("🎉 Scheduled payments including Jonah are working perfectly!")
        else:
            print("\n💥 Some tests failed!")
            exit(1)
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)