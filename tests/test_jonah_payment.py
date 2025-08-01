#!/usr/bin/env python3
"""
Test script to verify Jonah payment calculation and integration works correctly.
"""

import tempfile
from pathlib import Path
from datetime import date
from decimal import Decimal

from family_mobile_ledger.datatypes import LedgerRow
from family_mobile_ledger.scheduled import (
    jonah_payment_for_bill, add_jonah_payment_if_missing
)
from family_mobile_ledger.ledger_updater import read_ledger, write_full_ledger

def test_jonah_payment_calculation():
    """Test the Jonah payment calculation function"""
    print("🧪 Testing Jonah payment calculation...")
    
    # Create sample T-Mobile bill entries
    due_date = date(2025, 6, 24)
    
    bill_rows = [
        LedgerRow(
            description="10 voice lines",
            date=due_date,
            amount=Decimal('280.00'),
            category='service',
            shares_jj=2, shares_ks=6, shares_dj=1, shares_re=2,
            shares_total=11,
            jj=Decimal('50.91'),  # JJ's portion
            ks=Decimal('152.73'),
            dj=Decimal('25.45'),
            re=Decimal('50.91')
        ),
        LedgerRow(
            description="3 wearable plans",
            date=due_date,
            amount=Decimal('54.00'),
            category='service',
            shares_jj=None, shares_ks=2, shares_dj=None, shares_re=1,
            shares_total=3,
            jj=Decimal('0.00'),  # JJ has no wearables
            ks=Decimal('36.00'),
            dj=Decimal('0.00'),
            re=Decimal('18.00')
        ),
        LedgerRow(
            description="jonah iphone",
            date=due_date,
            amount=Decimal('33.34'),
            category='equipment',
            shares_jj=1, shares_ks=None, shares_dj=None, shares_re=None,
            shares_total=1,
            jj=Decimal('33.34'),  # JJ's equipment
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
            jj=Decimal('4.50'),  # JJ's Netflix portion
            ks=Decimal('4.50'),
            dj=Decimal('4.50'),
            re=Decimal('4.50')
        )
    ]
    
    # Calculate Jonah's payment
    jonah_payment = jonah_payment_for_bill(bill_rows, due_date)
    
    # Verify the payment was calculated correctly
    assert jonah_payment is not None, "Jonah payment should be calculated"
    
    expected_total = Decimal('50.91') + Decimal('0.00') + Decimal('33.34') + Decimal('4.50')
    expected_payment = -expected_total  # Negative because it's a payment
    
    assert jonah_payment.amount == expected_payment, f"Expected {expected_payment}, got {jonah_payment.amount}"
    assert jonah_payment.description == "Jonah", f"Expected 'Jonah', got '{jonah_payment.description}'"
    assert jonah_payment.date == due_date, f"Expected {due_date}, got {jonah_payment.date}"
    assert jonah_payment.category == "payment", f"Expected 'payment', got '{jonah_payment.category}'"
    assert jonah_payment.jj == expected_payment, f"Expected JJ cost {expected_payment}, got {jonah_payment.jj}"
    
    print(f"✅ Jonah payment calculated correctly: {expected_payment}")
    print(f"✅ Total JJ costs covered: ${expected_total}")
    
    return True

def test_jonah_payment_integration():
    """Test the integration with existing ledger"""
    print("\n🧪 Testing Jonah payment integration...")
    
    # Create a temporary ledger
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        test_csv_path = Path(f.name)
    
    # Create existing ledger with some entries (no Jonah payment yet)
    due_date = date(2025, 6, 24)
    existing_ledger = [
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
        )
    ]
    
    # Write initial ledger
    write_full_ledger(test_csv_path, existing_ledger)
    
    # Read it back to test round-trip
    read_ledger_data = read_ledger(test_csv_path)
    assert len(read_ledger_data) == 1, f"Expected 1 entry, got {len(read_ledger_data)}"
    
    # Add Jonah payment if missing
    bill_rows = existing_ledger  # The bill entries we just added
    updated_ledger = add_jonah_payment_if_missing(read_ledger_data, bill_rows, due_date)
    
    # Verify Jonah payment was added
    assert len(updated_ledger) == 2, f"Expected 2 entries after adding Jonah payment, got {len(updated_ledger)}"
    
    jonah_entries = [row for row in updated_ledger if "jonah" in row.description.lower() and row.category == "payment"]
    assert len(jonah_entries) == 1, f"Expected 1 Jonah payment, got {len(jonah_entries)}"
    
    jonah_payment = jonah_entries[0]
    assert jonah_payment.amount == Decimal('-50.91'), f"Expected -50.91, got {jonah_payment.amount}"
    
    print("✅ Jonah payment integration works correctly")
    
    # Test duplicate prevention
    print("🧪 Testing duplicate prevention...")
    
    # Try to add Jonah payment again - should not create duplicate
    updated_again = add_jonah_payment_if_missing(updated_ledger, bill_rows, due_date)
    
    assert len(updated_again) == 2, f"Expected 2 entries (no duplicate), got {len(updated_again)}"
    
    jonah_entries_again = [row for row in updated_again if "jonah" in row.description.lower() and row.category == "payment"]
    assert len(jonah_entries_again) == 1, f"Expected 1 Jonah payment (no duplicate), got {len(jonah_entries_again)}"
    
    print("✅ Duplicate prevention works correctly")
    
    # Clean up
    test_csv_path.unlink()
    
    return True

def test_no_jj_costs():
    """Test case where bill has no JJ costs"""
    print("\n🧪 Testing bill with no JJ costs...")
    
    due_date = date(2025, 6, 24)
    
    # Bill with no JJ costs
    bill_rows = [
        LedgerRow(
            description="rebecca iphone",
            date=due_date,
            amount=Decimal('26.25'),
            category='equipment',
            shares_jj=None, shares_ks=None, shares_dj=None, shares_re=1,
            shares_total=1,
            jj=Decimal('0.00'),  # No JJ cost
            ks=Decimal('0.00'),
            dj=Decimal('0.00'),
            re=Decimal('26.25')
        )
    ]
    
    jonah_payment = jonah_payment_for_bill(bill_rows, due_date)
    
    assert jonah_payment is None, "Should not create Jonah payment when no JJ costs"
    
    print("✅ No Jonah payment created when no JJ costs")
    
    return True

if __name__ == '__main__':
    try:
        test1 = test_jonah_payment_calculation()
        test2 = test_jonah_payment_integration()
        test3 = test_no_jj_costs()
        
        if test1 and test2 and test3:
            print("\n🏆 All Jonah payment tests passed!")
        else:
            print("\n💥 Some tests failed!")
            exit(1)
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)