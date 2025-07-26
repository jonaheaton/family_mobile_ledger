import pandas as pd
from pathlib import Path
from .datatypes import LedgerRow
from decimal import Decimal

# Column order matching expenses.csv
COLUMNS = [
    'Date Posted',
    'Date Due', 
    'Amount',
    'Category',
    'Description',
    'Shares (JJ)',
    'Shares (KS)', 
    'Shares (DJ)',
    'Shares (RE)',
    'Shares (Total)',
    'Cost (JJ)',
    'Cost (KS)',
    'Cost (DJ)',
    'Cost (RE)'
]

def append_rows(csv_path: Path, rows: list[LedgerRow]) -> None:
    """Append LedgerRow objects to the expenses CSV file"""
    # Read existing CSV
    df_old = pd.read_csv(csv_path)
    
    # Convert LedgerRow objects to DataFrame format
    new_rows = []
    for row in rows:
        new_row = {
            'Date Posted': _format_date(row.date_posted),
            'Date Due': _format_date(row.date),
            'Amount': _format_money(row.amount),
            'Category': row.category,
            'Description': row.description,
            'Shares (JJ)': row.shares_jj,
            'Shares (KS)': row.shares_ks,
            'Shares (DJ)': row.shares_dj,
            'Shares (RE)': row.shares_re,
            'Shares (Total)': row.shares_total,
            'Cost (JJ)': _format_money(row.jj),
            'Cost (KS)': _format_money(row.ks),
            'Cost (DJ)': _format_money(row.dj),
            'Cost (RE)': _format_money(row.re),
        }
        new_rows.append(new_row)
    
    df_new = pd.DataFrame(new_rows)
    
    # Combine and save
    df_combined = pd.concat([df_old, df_new], ignore_index=True)
    df_combined.to_csv(csv_path, index=False)

def _format_date(date_obj):
    """Format date for CSV - return None if None so pandas handles it correctly"""
    if date_obj is None:
        return None
    return date_obj.strftime('%-m/%-d/%Y')  # Match CSV format like "1/24/2025"

def _format_money(amount):
    """Format money amount with $ prefix"""
    if amount == 0:
        return '$0.00'
    return f'${amount:.2f}'