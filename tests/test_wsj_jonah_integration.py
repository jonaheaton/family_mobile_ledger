#!/usr/bin/env python3
"""
Test script to verify WSJ charges automatically include Jonah payments.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date, timedelta
from decimal import Decimal
from family_mobile_ledger.datatypes import LedgerRow
from family_mobile_ledger.scheduled import wsj_charge, _create_wsj_jonah_payment

def test_wsj_jonah_payment_calculation():
    """Test that WSJ Jonah payment is calculated correctly"""
    print("🧪 Testing WSJ Jonah payment calculation...")
    
    wsj_date = date(2024, 9, 15)
    jonah_payment = _create_wsj_jonah_payment(wsj_date)
    
    # WSJ = $70.76, JJ share = 1/3, so Jonah pays $23.59 (rounded to match historical data)
    expected_amount = -Decimal('23.59')
    
    assert jonah_payment is not None, "Should create Jonah payment"
    assert jonah_payment.amount == expected_amount, f"Expected {expected_amount}, got {jonah_payment.amount}"
    assert jonah_payment.description == "Jonah", f"Expected 'Jonah', got '{jonah_payment.description}'"
    assert jonah_payment.date == wsj_date, f"Expected {wsj_date}, got {jonah_payment.date}"
    assert jonah_payment.category == "payment", f"Expected 'payment', got '{jonah_payment.category}'"
    assert jonah_payment.jj == expected_amount, f"Expected JJ cost {expected_amount}, got {jonah_payment.jj}"
    
    print(f"✅ WSJ Jonah payment calculated correctly: {expected_amount}")
    return True

def test_wsj_charge_with_jonah_payment():
    """Test that WSJ charges automatically include Jonah payments"""
    print("\n🧪 Testing WSJ charge with automatic Jonah payment...")
    
    # Start with empty ledger
    empty_ledger = []
    
    # Generate WSJ charges (which should include Jonah payments)
    updated_ledger = wsj_charge(empty_ledger)
    
    # Separate WSJ charges from Jonah payments
    wsj_charges = [row for row in updated_ledger if "WSJ" in row.description and row.category == "misc"]
    jonah_payments = [row for row in updated_ledger if "jonah" in row.description.lower() and row.category == "payment"]
    
    print(f"✅ Generated {len(wsj_charges)} WSJ charges")
    print(f"✅ Generated {len(jonah_payments)} Jonah payments")
    
    # Should have equal numbers of WSJ charges and Jonah payments
    assert len(wsj_charges) > 0, "Should have WSJ charges"
    assert len(jonah_payments) > 0, "Should have Jonah payments"
    assert len(wsj_charges) == len(jonah_payments), f"Should have equal WSJ charges ({len(wsj_charges)}) and Jonah payments ({len(jonah_payments)})"
    
    # Verify dates match between WSJ charges and Jonah payments
    wsj_dates = {row.date for row in wsj_charges}
    jonah_dates = {row.date for row in jonah_payments}
    
    assert wsj_dates == jonah_dates, "WSJ charge dates should match Jonah payment dates"
    print("✅ WSJ charges and Jonah payments have matching dates")
    
    # Verify amounts are correct
    for wsj_charge_row in wsj_charges:
        wsj_date = wsj_charge_row.date
        
        # Find corresponding Jonah payment
        jonah_payment_row = next(
            (row for row in jonah_payments if row.date == wsj_date),
            None
        )
        
        assert jonah_payment_row is not None, f"Missing Jonah payment for WSJ charge on {wsj_date}"
        
        # Verify WSJ charge
        assert wsj_charge_row.amount == Decimal('70.76'), f"WSJ charge should be $70.76, got {wsj_charge_row.amount}"
        assert wsj_charge_row.jj == Decimal('23.59'), f"WSJ JJ portion should be $23.59, got {wsj_charge_row.jj}"
        
        # Verify Jonah payment
        expected_jonah_amount = -Decimal('23.59')  # Negative because it's a payment
        assert jonah_payment_row.amount == expected_jonah_amount, f"Jonah payment should be {expected_jonah_amount}, got {jonah_payment_row.amount}"
        
    print("✅ All WSJ charges have correct corresponding Jonah payments")
    return True

def test_wsj_duplicate_prevention():
    """Test that duplicate WSJ charges and Jonah payments are not created"""
    print("\n🧪 Testing WSJ duplicate prevention...")
    
    # Create a ledger with existing WSJ charge and Jonah payment
    existing_date = date(2024, 9, 15)
    
    existing_ledger = [
        LedgerRow(
            description="WSJ",
            date=existing_date,
            amount=Decimal('70.76'),
            category='misc',
            shares_jj=1, shares_ks=0, shares_dj=2, shares_re=0,
            shares_total=3,
            jj=Decimal('23.59'),
            ks=Decimal('0.00'),
            dj=Decimal('47.17'),
            re=Decimal('0.00')
        ),
        LedgerRow(
            description="Jonah",
            date=existing_date,
            amount=Decimal('-23.59'),
            category='payment',
            shares_jj=1, shares_ks=None, shares_dj=None, shares_re=None,
            shares_total=1,
            jj=Decimal('-23.59'),
            ks=Decimal('0.00'),
            dj=Decimal('0.00'),
            re=Decimal('0.00')
        )
    ]
    
    # Try to add WSJ charges again
    updated_ledger = wsj_charge(existing_ledger)
    
    # Count entries for the existing date
    wsj_on_date = [row for row in updated_ledger if row.date == existing_date and "WSJ" in row.description]
    jonah_on_date = [row for row in updated_ledger if row.date == existing_date and "jonah" in row.description.lower() and row.category == "payment"]
    
    assert len(wsj_on_date) == 1, f"Should have exactly 1 WSJ charge on {existing_date}, got {len(wsj_on_date)}"
    assert len(jonah_on_date) == 1, f"Should have exactly 1 Jonah payment on {existing_date}, got {len(jonah_on_date)}"
    
    print("✅ No duplicate WSJ charges or Jonah payments created")
    return True

def test_wsj_partial_duplicate_handling():
    """Test handling when WSJ charge exists but Jonah payment is missing"""
    print("\n🧪 Testing partial duplicate handling...")
    
    # Create ledger with WSJ charge but missing Jonah payment
    existing_date = date(2024, 9, 15)
    
    existing_ledger = [
        LedgerRow(
            description="WSJ",
            date=existing_date,
            amount=Decimal('70.76'),
            category='misc',
            shares_jj=1, shares_ks=0, shares_dj=2, shares_re=0,
            shares_total=3,
            jj=Decimal('23.59'),
            ks=Decimal('0.00'),
            dj=Decimal('47.17'),
            re=Decimal('0.00')
        )
        # Note: No Jonah payment for this date
    ]
    
    # Run WSJ charge function
    updated_ledger = wsj_charge(existing_ledger)
    
    # Should have added the missing Jonah payment
    wsj_on_date = [row for row in updated_ledger if row.date == existing_date and "WSJ" in row.description]
    jonah_on_date = [row for row in updated_ledger if row.date == existing_date and "jonah" in row.description.lower() and row.category == "payment"]
    
    assert len(wsj_on_date) == 1, f"Should still have 1 WSJ charge on {existing_date}, got {len(wsj_on_date)}"
    assert len(jonah_on_date) == 1, f"Should have added 1 Jonah payment on {existing_date}, got {len(jonah_on_date)}"
    
    # Verify the added Jonah payment is correct
    jonah_payment = jonah_on_date[0]
    expected_amount = -Decimal('23.59')
    assert jonah_payment.amount == expected_amount, f"Expected {expected_amount}, got {jonah_payment.amount}"
    
    print("✅ Missing Jonah payment was correctly added for existing WSJ charge")
    return True

def test_wsj_schedule_consistency():
    """Test that WSJ charges maintain 4-week schedule"""
    print("\n🧪 Testing WSJ 4-week schedule consistency...")
    
    empty_ledger = []
    updated_ledger = wsj_charge(empty_ledger)
    
    # Get all WSJ charge dates
    wsj_charges = [row for row in updated_ledger if "WSJ" in row.description and row.category == "misc"]
    wsj_dates = sorted([row.date for row in wsj_charges])
    
    # Verify 4-week (28-day) intervals
    for i in range(1, len(wsj_dates)):
        days_diff = (wsj_dates[i] - wsj_dates[i-1]).days
        assert days_diff == 28, f"WSJ charges should be 28 days apart, got {days_diff} days between {wsj_dates[i-1]} and {wsj_dates[i]}"
    
    print(f"✅ All {len(wsj_dates)} WSJ charges maintain 4-week schedule")
    return True

if __name__ == '__main__':
    try:
        test1 = test_wsj_jonah_payment_calculation()
        test2 = test_wsj_charge_with_jonah_payment()
        test3 = test_wsj_duplicate_prevention()
        test4 = test_wsj_partial_duplicate_handling()
        test5 = test_wsj_schedule_consistency()
        
        if all([test1, test2, test3, test4, test5]):
            print("\n🏆 All WSJ + Jonah payment tests passed!")
            print("🎉 WSJ charges now automatically include Jonah payments!")
        else:
            print("\n💥 Some tests failed!")
            exit(1)
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)