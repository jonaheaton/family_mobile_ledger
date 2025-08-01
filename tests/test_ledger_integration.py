#!/usr/bin/env python3
"""
Simple integration test for the updated ledger_updater.py
"""
import tempfile
import pandas as pd
from pathlib import Path
from datetime import date
from decimal import Decimal

# Import the modules
import sys
sys.path.append('family_mobile_ledger')
from family_mobile_ledger.datatypes import LedgerRow
from family_mobile_ledger.ledger_updater import append_rows

def test_ledger_updater():
    """Test that the ledger_updater correctly formats and appends rows"""
    
    # Create a temporary CSV file with the expenses.csv format
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        # Write header matching expenses.csv
        f.write('Date Posted,Date Due,Amount,Category,Description,Shares (JJ),Shares (KS),Shares (DJ),Shares (RE),Shares (Total),Cost (JJ),Cost (KS),Cost (DJ),Cost (RE)\n')
        # Write one existing row
        f.write(',1/1/2025,$100.00,service,existing entry,1,1,1,1,4,$25.00,$25.00,$25.00,$25.00\n')
        temp_path = Path(f.name)
    
    try:
        # Create test LedgerRow objects matching new format
        test_rows = [
            LedgerRow(
                description="test service",
                date=date(2025, 1, 15),
                amount=Decimal("50.00"),
                category="service",
                date_posted=date(2025, 1, 10),
                shares_jj=2,
                shares_ks=1,
                shares_dj=1,
                shares_re=2,
                shares_total=6,
                jj=Decimal("16.67"),
                ks=Decimal("8.33"),
                dj=Decimal("8.33"),
                re=Decimal("16.67")
            ),
            LedgerRow(
                description="test equipment",
                date=date(2025, 1, 15), 
                amount=Decimal("30.00"),
                category="equipment",
                shares_jj=1,
                shares_total=1,
                jj=Decimal("30.00")
            )
        ]
        
        # Append the rows
        append_rows(temp_path, test_rows)
        
        # Read back and verify
        df = pd.read_csv(temp_path)
        
        print("CSV content after append:")
        print(df.to_string())
        print()
        
        # Verify structure
        expected_columns = [
            'Date Posted', 'Date Due', 'Amount', 'Category', 'Description',
            'Shares (JJ)', 'Shares (KS)', 'Shares (DJ)', 'Shares (RE)', 'Shares (Total)',
            'Cost (JJ)', 'Cost (KS)', 'Cost (DJ)', 'Cost (RE)'
        ]
        
        assert list(df.columns) == expected_columns
        assert len(df) == 3  # 1 existing + 2 new
        
        # Check the new rows
        service_row = df[df['Description'] == 'test service'].iloc[0]
        assert service_row['Date Posted'] == '1/10/2025'
        assert service_row['Date Due'] == '1/15/2025'
        assert service_row['Amount'] == '$50.00'
        assert service_row['Category'] == 'service'
        assert service_row['Shares (JJ)'] == 2
        assert service_row['Cost (JJ)'] == '$16.67'
        
        equipment_row = df[df['Description'] == 'test equipment'].iloc[0]
        assert pd.isna(equipment_row['Date Posted'])  # None should become NaN
        assert equipment_row['Amount'] == '$30.00'
        assert equipment_row['Category'] == 'equipment'
        assert pd.isna(equipment_row['Shares (KS)'])  # None should become NaN
        assert equipment_row['Cost (JJ)'] == '$30.00'
        assert equipment_row['Cost (KS)'] == '$0.00'
        
        print("✅ All tests passed!")
        
    finally:
        # Clean up
        temp_path.unlink()

if __name__ == "__main__":
    test_ledger_updater()