#!/usr/bin/env python3
"""
Test script to verify the CLI integration with scheduled payments works correctly.
"""

import tempfile
import pandas as pd
from pathlib import Path
from datetime import date
from decimal import Decimal

from family_mobile_ledger.ledger_updater import read_ledger, write_full_ledger
from family_mobile_ledger.scheduled import update_all_scheduled
from family_mobile_ledger.datatypes import LedgerRow

def test_cli_integration():
    """Test the full integration flow"""
    print("🧪 Testing CLI integration with scheduled payments...")
    
    # Create a temporary CSV file with some existing data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        test_csv_path = Path(f.name)
    
    # Create some sample existing data (as if from a previous run)
    sample_data = {
        'Date Posted': ['1/15/2025'],
        'Date Due': ['1/15/2025'],
        'Amount': ['-$77.00'],
        'Category': ['payment'],
        'Description': ['Seth R Eaton'],
        'Shares (JJ)': [None],
        'Shares (KS)': [1.0],
        'Shares (DJ)': [None],
        'Shares (RE)': [None],
        'Shares (Total)': [1],
        'Cost (JJ)': ['$0.00'],
        'Cost (KS)': ['-$77.00'],
        'Cost (DJ)': ['$0.00'],
        'Cost (RE)': ['$0.00']
    }
    
    df = pd.DataFrame(sample_data)
    df.to_csv(test_csv_path, index=False)
    print(f"✅ Created test CSV with {len(df)} existing entries")
    
    # Test 1: Read the ledger
    print("\n📖 Testing ledger reading...")
    existing_ledger = read_ledger(test_csv_path)
    print(f"✅ Read {len(existing_ledger)} entries from CSV")
    
    # Verify the data was read correctly
    assert len(existing_ledger) == 1
    assert existing_ledger[0].description == "Seth R Eaton"
    assert existing_ledger[0].amount == Decimal('-77.00')
    assert existing_ledger[0].ks == Decimal('-77.00')
    print("✅ Ledger data parsed correctly")
    
    # Test 2: Apply scheduled updates
    print("\n📅 Testing scheduled payment updates...")
    updated_ledger = update_all_scheduled(existing_ledger)
    new_entries = len(updated_ledger) - len(existing_ledger)
    print(f"✅ Added {new_entries} new scheduled entries")
    
    # Test 3: Write back to CSV
    print("\n💾 Testing full ledger write...")
    write_full_ledger(test_csv_path, updated_ledger)
    print("✅ Successfully wrote updated ledger to CSV")
    
    # Test 4: Verify the round-trip works
    print("\n🔄 Testing round-trip consistency...")
    reread_ledger = read_ledger(test_csv_path)
    print(f"✅ Re-read ledger has {len(reread_ledger)} entries")
    
    # Verify no duplicates were created
    descriptions_and_dates = [(row.description, row.date) for row in reread_ledger]
    unique_combinations = set(descriptions_and_dates)
    if len(descriptions_and_dates) == len(unique_combinations):
        print("✅ No duplicate entries detected")
    else:
        print("❌ Duplicate entries found!")
        return False
    
    # Clean up
    test_csv_path.unlink()
    print(f"🧹 Cleaned up test file")
    
    print("\n🎉 All integration tests passed!")
    return True

def test_scheduled_payment_types():
    """Test that all expected scheduled payment types are working"""
    print("\n🔍 Testing individual scheduled payment types...")
    
    empty_ledger = []
    updated_ledger = update_all_scheduled(empty_ledger)
    
    # Check for each payment type
    enrique_entries = [row for row in updated_ledger if "Enrique" in row.description]
    daniel_entries = [row for row in updated_ledger if "Daniel" in row.description]
    seth_entries = [row for row in updated_ledger if "Seth" in row.description]
    wsj_entries = [row for row in updated_ledger if "WSJ" in row.description]
    
    print(f"✅ Enrique payments: {len(enrique_entries)} entries")
    print(f"✅ Daniel payments: {len(daniel_entries)} entries")
    print(f"✅ Seth payments: {len(seth_entries)} entries")
    print(f"✅ WSJ charges: {len(wsj_entries)} entries")
    
    # Verify amounts are correct
    if enrique_entries:
        assert enrique_entries[0].amount == Decimal('-105.59')
        print("✅ Enrique payment amount correct")
    
    if daniel_entries:
        assert daniel_entries[0].amount == Decimal('-69.73')
        print("✅ Daniel payment amount correct")
    
    if seth_entries:
        assert seth_entries[0].amount == Decimal('-77.00')
        print("✅ Seth payment amount correct")
    
    if wsj_entries:
        assert wsj_entries[0].amount == Decimal('70.76')
        print("✅ WSJ charge amount correct")
    
    return True

if __name__ == '__main__':
    try:
        success1 = test_cli_integration()
        success2 = test_scheduled_payment_types()
        
        if success1 and success2:
            print("\n🏆 All tests passed! CLI integration is working correctly.")
        else:
            print("\n💥 Some tests failed!")
            exit(1)
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)