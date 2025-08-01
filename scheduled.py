"""
Scheduled payment and expense module.

This module handles recurring payments and charges that occur on predictable schedules.
Each function takes a ledger (list of LedgerRow objects) and adds missing scheduled
entries up to the current date, being careful not to duplicate existing entries.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Set

try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    # Fallback implementation if dateutil is not available
    def relativedelta(months=0):
        """Simple fallback for adding months - approximate using 30 days per month"""
        return timedelta(days=months * 30)

from .datatypes import LedgerRow

# Set up module logger
logger = logging.getLogger(__name__)

def _get_existing_entries(ledger: List[LedgerRow], description_pattern: str) -> Set[date]:
    """
    Get set of dates that already have entries matching the description pattern.
    This helps avoid duplicating scheduled entries.
    """
    existing_dates = set()
    for row in ledger:
        if description_pattern.lower() in row.description.lower():
            existing_dates.add(row.date)
    return existing_dates

def _create_payment_row(description: str, payment_date: date, amount: Decimal, 
                       family: str) -> LedgerRow:
    """Create a payment LedgerRow for the specified family."""
    # Map family codes to share allocation
    family_shares = {'JJ': 0, 'KS': 0, 'DJ': 0, 'RE': 0}
    family_costs = {'JJ': Decimal('0'), 'KS': Decimal('0'), 
                   'DJ': Decimal('0'), 'RE': Decimal('0')}
    
    if family == 'RE':
        family_shares['RE'] = 1
        family_costs['RE'] = amount
    elif family == 'DJ':
        family_shares['DJ'] = 1
        family_costs['DJ'] = amount
    elif family == 'KS':
        family_shares['KS'] = 1
        family_costs['KS'] = amount
    elif family == 'JJ':
        family_shares['JJ'] = 1
        family_costs['JJ'] = amount
    
    return LedgerRow(
        description=description,
        date=payment_date,
        amount=amount,
        category='payment',
        shares_jj=family_shares['JJ'] or None,
        shares_ks=family_shares['KS'] or None,
        shares_dj=family_shares['DJ'] or None,
        shares_re=family_shares['RE'] or None,
        shares_total=1,
        jj=family_costs['JJ'],
        ks=family_costs['KS'],
        dj=family_costs['DJ'],
        re=family_costs['RE']
    )

def _create_expense_row(description: str, expense_date: date, amount: Decimal,
                       shares_jj: int = 0, shares_ks: int = 0, 
                       shares_dj: int = 0, shares_re: int = 0) -> LedgerRow:
    """Create an expense LedgerRow with specified share allocation."""
    total_shares = shares_jj + shares_ks + shares_dj + shares_re
    
    if total_shares == 0:
        raise ValueError("At least one family must have shares")
    
    # Calculate costs based on shares
    cost_per_share = amount / Decimal(total_shares)
    
    return LedgerRow(
        description=description,
        date=expense_date,
        amount=amount,
        category='misc',
        shares_jj=shares_jj or None,
        shares_ks=shares_ks or None,
        shares_dj=shares_dj or None,
        shares_re=shares_re or None,
        shares_total=total_shares,
        jj=cost_per_share * Decimal(shares_jj),
        ks=cost_per_share * Decimal(shares_ks),
        dj=cost_per_share * Decimal(shares_dj),
        re=cost_per_share * Decimal(shares_re)
    )

def enrique_payment(ledger: List[LedgerRow]) -> List[LedgerRow]:
    """
    Add Enrique's monthly payments of $105.59, typically made around the 6th of each month.
    
    Based on expenses.csv pattern:
    - Amount: -$105.59 (negative because it's a payment)
    - Schedule: Monthly around 6th-8th
    - Assigned to: RE family
    - Started: Around January 2025 with the new amount
    """
    logger.info("Processing Enrique payment schedule...")
    
    # Check existing entries to avoid duplicates
    existing_dates = _get_existing_entries(ledger, "Enrique")
    logger.debug(f"Found {len(existing_dates)} existing Enrique payment entries")
    
    new_entries = []
    today = date.today()
    
    # Start from January 2025 when the $105.59 amount began
    start_date = date(2025, 1, 6)
    current_date = start_date
    
    while current_date <= today:
        if current_date not in existing_dates:
            payment_row = _create_payment_row(
                description="Enrique Gonzalez",
                payment_date=current_date,
                amount=Decimal('-105.59'),
                family='RE'
            )
            new_entries.append(payment_row)
            logger.info(f"Added Enrique payment for {current_date}: -$105.59")
        else:
            logger.debug(f"Enrique payment already exists for {current_date}")
        
        # Move to next month, keeping the 6th as the target day
        current_date = current_date + relativedelta(months=1)
    
    logger.info(f"Added {len(new_entries)} new Enrique payment entries")
    return ledger + new_entries

def daniel_payment(ledger: List[LedgerRow]) -> List[LedgerRow]:
    """
    Add Daniel's monthly payments of $69.73, typically made around the 3rd-7th of each month.
    
    Based on expenses.csv pattern:
    - Amount: -$69.73 (negative because it's a payment)
    - Schedule: Monthly around 3rd-7th
    - Assigned to: DJ family
    - Started: Around January 2025
    """
    logger.info("Processing Daniel payment schedule...")
    
    existing_dates = _get_existing_entries(ledger, "Daniel")
    logger.debug(f"Found {len(existing_dates)} existing Daniel payment entries")
    
    new_entries = []
    today = date.today()
    
    # Start from January 2025, using 3rd as the target day
    start_date = date(2025, 1, 3)
    current_date = start_date
    
    while current_date <= today:
        if current_date not in existing_dates:
            payment_row = _create_payment_row(
                description="Daniel Eaton",
                payment_date=current_date,
                amount=Decimal('-69.73'),
                family='DJ'
            )
            new_entries.append(payment_row)
            logger.info(f"Added Daniel payment for {current_date}: -$69.73")
        else:
            logger.debug(f"Daniel payment already exists for {current_date}")
        
        # Move to next month, keeping the 3rd as the target day
        current_date = current_date + relativedelta(months=1)
    
    logger.info(f"Added {len(new_entries)} new Daniel payment entries")
    return ledger + new_entries

def seth_payment(ledger: List[LedgerRow]) -> List[LedgerRow]:
    """
    Add Seth's monthly payments of $77.00, made on the 15th of each month.
    
    Based on expenses.csv pattern:
    - Amount: -$77.00 (negative because it's a payment)
    - Schedule: Monthly on the 15th
    - Assigned to: KS family
    - Very consistent schedule
    """
    logger.info("Processing Seth payment schedule...")
    
    existing_dates = _get_existing_entries(ledger, "Seth")
    logger.debug(f"Found {len(existing_dates)} existing Seth payment entries")
    
    new_entries = []
    today = date.today()
    
    # Start from January 2024 based on historical data
    start_date = date(2024, 1, 15)
    current_date = start_date
    
    while current_date <= today:
        if current_date not in existing_dates:
            payment_row = _create_payment_row(
                description="Seth R Eaton",
                payment_date=current_date,
                amount=Decimal('-77.00'),
                family='KS'
            )
            new_entries.append(payment_row)
            logger.info(f"Added Seth payment for {current_date}: -$77.00")
        else:
            logger.debug(f"Seth payment already exists for {current_date}")
        
        # Move to next month, keeping the 15th as the target day
        current_date = current_date + relativedelta(months=1)
    
    logger.info(f"Added {len(new_entries)} new Seth payment entries")
    return ledger + new_entries

def wsj_charge(ledger: List[LedgerRow]) -> List[LedgerRow]:
    """
    Add Wall Street Journal subscription charges of $70.76, charged every 4 weeks.
    
    Based on expenses.csv pattern:
    - Amount: $70.76 (positive because it's an expense)
    - Schedule: Every 4 weeks (28 days)
    - Share allocation: JJ=1, DJ=2 (so DJ pays 2/3, JJ pays 1/3)
    - Started appearing around September 2024
    """
    logger.info("Processing WSJ charge schedule (every 4 weeks)...")
    
    existing_dates = _get_existing_entries(ledger, "WSJ")
    logger.debug(f"Found {len(existing_dates)} existing WSJ charge entries")
    
    new_entries = []
    today = date.today()
    
    # Start from the first observed WSJ charge and generate every 4 weeks
    start_date = date(2024, 9, 15)  # First observed in expenses.csv
    current_date = start_date
    
    while current_date <= today:
        if current_date not in existing_dates:
            expense_row = _create_expense_row(
                description="WSJ",
                expense_date=current_date,
                amount=Decimal('70.76'),
                shares_jj=1,
                shares_dj=2,
                shares_ks=0,
                shares_re=0
            )
            new_entries.append(expense_row)
            logger.info(f"Added WSJ charge for {current_date}: $70.76 (JJ: $23.59, DJ: $47.17)")
        else:
            logger.debug(f"WSJ charge already exists for {current_date}")
        
        # Move to next charge date (4 weeks = 28 days later)
        current_date = current_date + timedelta(days=28)
    
    logger.info(f"Added {len(new_entries)} new WSJ charge entries")
    return ledger + new_entries

def update_all_scheduled(ledger: List[LedgerRow]) -> List[LedgerRow]:
    """
    Apply all scheduled payment and expense rules to bring the ledger up to date.
    
    This is a convenience function that applies all the individual schedule functions
    in the correct order.
    """
    logger.info("Starting comprehensive scheduled update...")
    
    original_count = len(ledger)
    
    # Apply all scheduled updates
    ledger = enrique_payment(ledger)
    ledger = daniel_payment(ledger)
    ledger = seth_payment(ledger)
    ledger = wsj_charge(ledger)
    
    new_count = len(ledger)
    total_added = new_count - original_count
    
    logger.info(f"Scheduled update complete: added {total_added} entries total")
    
    return ledger