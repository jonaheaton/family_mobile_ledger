import pandas as pd
from pathlib import Path
from .datatypes import LedgerRow
from decimal import Decimal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

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
    # Read existing CSV or create empty DataFrame
    if csv_path.exists():
        df_old = pd.read_csv(csv_path)
    else:
        df_old = pd.DataFrame(columns=COLUMNS)
    
    # Convert LedgerRow objects to DataFrame format
    new_rows = []
    for row in rows:
        new_row = _ledger_row_to_dict(row)
        new_rows.append(new_row)
    
    df_new = pd.DataFrame(new_rows)
    
    # Combine and save
    df_combined = pd.concat([df_old, df_new], ignore_index=True)
    df_combined.to_csv(csv_path, index=False)

def write_full_ledger(csv_path: Path, ledger_rows: list[LedgerRow]) -> None:
    """Write the complete ledger to CSV, replacing any existing file"""
    logger.info(f"Writing {len(ledger_rows)} ledger entries to {csv_path}")
    
    # Convert all LedgerRow objects to DataFrame format
    rows_data = []
    for row in ledger_rows:
        row_dict = _ledger_row_to_dict(row)
        rows_data.append(row_dict)
    
    df = pd.DataFrame(rows_data, columns=COLUMNS)
    df.to_csv(csv_path, index=False)
    logger.debug(f"Successfully wrote ledger to {csv_path}")

def _ledger_row_to_dict(row: LedgerRow) -> dict:
    """Convert a LedgerRow to dictionary format for CSV writing"""
    return {
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

def read_ledger(csv_path: Path) -> list[LedgerRow]:
    """Read the existing ledger CSV and convert to LedgerRow objects"""
    if not csv_path.exists():
        logger.info(f"Ledger file {csv_path} does not exist, returning empty ledger")
        return []
    
    df = pd.read_csv(csv_path)
    logger.debug(f"Read {len(df)} rows from {csv_path}")
    
    ledger_rows = []
    for _, row in df.iterrows():
        # Parse dates
        date_posted = _parse_date(row.get('Date Posted'))
        date_due = _parse_date(row.get('Date Due'))
        
        # Parse money amounts (remove $ prefix and convert to Decimal)
        amount = _parse_money(row.get('Amount'))
        jj_cost = _parse_money(row.get('Cost (JJ)'))
        ks_cost = _parse_money(row.get('Cost (KS)'))
        dj_cost = _parse_money(row.get('Cost (DJ)'))
        re_cost = _parse_money(row.get('Cost (RE)'))
        
        # Parse shares (handle None/NaN values)
        shares_jj = _parse_share(row.get('Shares (JJ)'))
        shares_ks = _parse_share(row.get('Shares (KS)'))
        shares_dj = _parse_share(row.get('Shares (DJ)'))
        shares_re = _parse_share(row.get('Shares (RE)'))
        shares_total = int(row.get('Shares (Total)', 0))
        
        ledger_row = LedgerRow(
            description=str(row.get('Description', '')),
            date=date_due,
            date_posted=date_posted,
            amount=amount,
            category=str(row.get('Category', '')),
            shares_jj=shares_jj,
            shares_ks=shares_ks,
            shares_dj=shares_dj,
            shares_re=shares_re,
            shares_total=shares_total,
            jj=jj_cost,
            ks=ks_cost,
            dj=dj_cost,
            re=re_cost
        )
        ledger_rows.append(ledger_row)
    
    logger.info(f"Converted {len(ledger_rows)} CSV rows to LedgerRow objects")
    return ledger_rows

def _parse_date(date_str):
    """Parse date string from CSV format, handle None/empty values"""
    if pd.isna(date_str) or date_str == '' or date_str is None:
        return None
    
    # Handle various date formats in the CSV
    try:
        # Try MM/DD/YYYY format first
        return datetime.strptime(str(date_str), '%m/%d/%Y').date()
    except ValueError:
        try:
            # Try M/D/YYYY format
            return datetime.strptime(str(date_str), '%m/%d/%Y').date()
        except ValueError:
            logger.warning(f"Could not parse date: {date_str}")
            return None

def _parse_money(money_str):
    """Parse money string, remove $ prefix and convert to Decimal"""
    if pd.isna(money_str) or money_str == '' or money_str is None:
        return Decimal('0')
    
    # Remove $ prefix and any whitespace
    clean_str = str(money_str).replace('$', '').strip()
    if clean_str == '':
        return Decimal('0')
    
    try:
        return Decimal(clean_str)
    except:
        logger.warning(f"Could not parse money amount: {money_str}")
        return Decimal('0')

def _parse_share(share_value):
    """Parse share value, handle None/NaN and convert to int or None"""
    if pd.isna(share_value) or share_value == '' or share_value is None:
        return None
    
    try:
        value = float(share_value)
        return int(value) if value != 0 else None
    except:
        return None