"""
Scheduled payment and expense module.

This module handles recurring payments and charges that occur on predictable schedules.
Each function takes a ledger (list of LedgerRow objects) and adds missing scheduled
entries up to the current date, being careful not to duplicate existing entries.
"""

import logging
import yaml
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Set, Dict, Any
from pathlib import Path

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

# Configuration loading
_config_cache = None

def _get_config_path() -> Path:
    """Get the path to the scheduled payments configuration file"""
    # Look for config file in the same data directory as family_config.yaml
    module_dir = Path(__file__).parent
    config_path = module_dir / "data" / "scheduled_config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Scheduled payments config not found at {config_path}")
    
    return config_path

def _load_config() -> Dict[str, Any]:
    """Load the scheduled payments configuration from YAML file"""
    global _config_cache
    
    if _config_cache is not None:
        return _config_cache
    
    config_path = _get_config_path()
    logger.debug(f"Loading scheduled payments config from {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        _config_cache = config
        logger.info(f"Loaded scheduled payments configuration (version {config.get('metadata', {}).get('config_version', 'unknown')})")
        return config
        
    except Exception as e:
        logger.error(f"Failed to load scheduled payments config: {e}")
        raise

def _parse_config_date(date_str: str) -> date:
    """Parse a date string from the config file"""
    return datetime.strptime(date_str, "%Y-%m-%d").date()

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
    Add Enrique's monthly payments based on configuration.
    """
    config = _load_config()
    enrique_config = config['monthly_payments']['enrique']
    
    if not enrique_config.get('enabled', True):
        logger.info("Enrique payment is disabled in configuration")
        return ledger
    
    logger.info("Processing Enrique payment schedule...")
    
    # Check existing entries to avoid duplicates
    existing_dates = _get_existing_entries(ledger, enrique_config['description'])
    logger.debug(f"Found {len(existing_dates)} existing Enrique payment entries")
    
    new_entries = []
    today = date.today()
    
    # Get configuration values
    start_date = _parse_config_date(enrique_config['start_date'])
    amount = Decimal(str(enrique_config['amount']))
    day_of_month = enrique_config['day_of_month']
    family = enrique_config['family']
    description = enrique_config['description']
    
    # Generate monthly payments from start date to today
    current_date = start_date.replace(day=day_of_month)
    
    # Ensure we start from the correct month
    if current_date < start_date:
        current_date = current_date + relativedelta(months=1)
    
    while current_date <= today:
        if current_date not in existing_dates:
            payment_row = _create_payment_row(
                description=description,
                payment_date=current_date,
                amount=amount,
                family=family
            )
            new_entries.append(payment_row)
            logger.info(f"Added Enrique payment for {current_date}: {amount}")
        else:
            logger.debug(f"Enrique payment already exists for {current_date}")
        
        # Move to next month, keeping the target day
        current_date = current_date + relativedelta(months=1)
    
    logger.info(f"Added {len(new_entries)} new Enrique payment entries")
    return ledger + new_entries

def daniel_payment(ledger: List[LedgerRow]) -> List[LedgerRow]:
    """
    Add Daniel's monthly payments based on configuration.
    """
    config = _load_config()
    daniel_config = config['monthly_payments']['daniel']
    
    if not daniel_config.get('enabled', True):
        logger.info("Daniel payment is disabled in configuration")
        return ledger
    
    logger.info("Processing Daniel payment schedule...")
    
    existing_dates = _get_existing_entries(ledger, daniel_config['description'])
    logger.debug(f"Found {len(existing_dates)} existing Daniel payment entries")
    
    new_entries = []
    today = date.today()
    
    # Get configuration values
    start_date = _parse_config_date(daniel_config['start_date'])
    amount = Decimal(str(daniel_config['amount']))
    day_of_month = daniel_config['day_of_month']
    family = daniel_config['family']
    description = daniel_config['description']
    
    # Generate monthly payments from start date to today
    current_date = start_date.replace(day=day_of_month)
    
    # Ensure we start from the correct month
    if current_date < start_date:
        current_date = current_date + relativedelta(months=1)
    
    while current_date <= today:
        if current_date not in existing_dates:
            payment_row = _create_payment_row(
                description=description,
                payment_date=current_date,
                amount=amount,
                family=family
            )
            new_entries.append(payment_row)
            logger.info(f"Added Daniel payment for {current_date}: {amount}")
        else:
            logger.debug(f"Daniel payment already exists for {current_date}")
        
        # Move to next month, keeping the target day
        current_date = current_date + relativedelta(months=1)
    
    logger.info(f"Added {len(new_entries)} new Daniel payment entries")
    return ledger + new_entries

def seth_payment(ledger: List[LedgerRow]) -> List[LedgerRow]:
    """
    Add Seth's monthly payments based on configuration.
    """
    config = _load_config()
    seth_config = config['monthly_payments']['seth']
    
    if not seth_config.get('enabled', True):
        logger.info("Seth payment is disabled in configuration")
        return ledger
    
    logger.info("Processing Seth payment schedule...")
    
    existing_dates = _get_existing_entries(ledger, seth_config['description'])
    logger.debug(f"Found {len(existing_dates)} existing Seth payment entries")
    
    new_entries = []
    today = date.today()
    
    # Get configuration values
    start_date = _parse_config_date(seth_config['start_date'])
    amount = Decimal(str(seth_config['amount']))
    day_of_month = seth_config['day_of_month']
    family = seth_config['family']
    description = seth_config['description']
    
    # Generate monthly payments from start date to today
    current_date = start_date.replace(day=day_of_month)
    
    # Ensure we start from the correct month
    if current_date < start_date:
        current_date = current_date + relativedelta(months=1)
    
    while current_date <= today:
        if current_date not in existing_dates:
            payment_row = _create_payment_row(
                description=description,
                payment_date=current_date,
                amount=amount,
                family=family
            )
            new_entries.append(payment_row)
            logger.info(f"Added Seth payment for {current_date}: {amount}")
        else:
            logger.debug(f"Seth payment already exists for {current_date}")
        
        # Move to next month, keeping the target day
        current_date = current_date + relativedelta(months=1)
    
    logger.info(f"Added {len(new_entries)} new Seth payment entries")
    return ledger + new_entries

def wsj_charge(ledger: List[LedgerRow]) -> List[LedgerRow]:
    """
    Add Wall Street Journal subscription charges based on configuration.
    Also automatically adds Jonah's payment for his share if configured.
    """
    config = _load_config()
    wsj_config = config['periodic_charges']['wsj']
    
    if not wsj_config.get('enabled', True):
        logger.info("WSJ charge is disabled in configuration")
        return ledger
    
    logger.info(f"Processing WSJ charge schedule (every {wsj_config['interval_days']} days)...")
    
    existing_wsj_dates = _get_existing_entries(ledger, wsj_config['description'])
    existing_jonah_dates = _get_existing_entries(ledger, "jonah")
    logger.debug(f"Found {len(existing_wsj_dates)} existing WSJ charge entries")
    logger.debug(f"Found {len(existing_jonah_dates)} existing Jonah payment entries")
    
    new_entries = []
    today = date.today()
    
    # Get configuration values
    start_date = _parse_config_date(wsj_config['start_date'])
    amount = Decimal(str(wsj_config['amount']))
    interval_days = wsj_config['interval_days']
    description = wsj_config['description']
    category = wsj_config['category']
    
    # Share and cost information
    shares = wsj_config['shares']
    costs = wsj_config['costs']
    
    current_date = start_date
    
    while current_date <= today:
        # Add WSJ charge if missing
        if current_date not in existing_wsj_dates:
            # Create WSJ expense with configured amounts
            expense_row = LedgerRow(
                description=description,
                date=current_date,
                amount=amount,
                category=category,
                shares_jj=shares.get('JJ', 0),
                shares_ks=shares.get('KS', 0),
                shares_dj=shares.get('DJ', 0),
                shares_re=shares.get('RE', 0),
                shares_total=sum(shares.values()),
                jj=Decimal(str(costs.get('JJ', 0))),
                ks=Decimal(str(costs.get('KS', 0))),
                dj=Decimal(str(costs.get('DJ', 0))),
                re=Decimal(str(costs.get('RE', 0)))
            )
            new_entries.append(expense_row)
            logger.info(f"Added WSJ charge for {current_date}: ${amount} (JJ: ${costs['JJ']}, DJ: ${costs['DJ']})")
            
            # Add Jonah's payment for WSJ if configured and missing
            if wsj_config.get('auto_jonah_payment', {}).get('enabled', False):
                jonah_payment = _create_wsj_jonah_payment_from_config(current_date, wsj_config)
                if jonah_payment and current_date not in existing_jonah_dates:
                    new_entries.append(jonah_payment)
                    logger.info(f"Added Jonah WSJ payment for {current_date}: {jonah_payment.amount}")
            
        else:
            logger.debug(f"WSJ charge already exists for {current_date}")
            
            # Even if WSJ charge exists, check if Jonah payment is missing
            if (wsj_config.get('auto_jonah_payment', {}).get('enabled', False) 
                and current_date not in existing_jonah_dates):
                # Check if there's already a Jonah payment specifically on this date
                existing_jonah_on_date = any(
                    row.date == current_date and "jonah" in row.description.lower() 
                    and row.category == "payment" for row in ledger
                )
                
                if not existing_jonah_on_date:
                    jonah_payment = _create_wsj_jonah_payment_from_config(current_date, wsj_config)
                    if jonah_payment:
                        new_entries.append(jonah_payment)
                        logger.info(f"Added missing Jonah WSJ payment for {current_date}: {jonah_payment.amount}")
        
        # Move to next charge date
        current_date = current_date + timedelta(days=interval_days)
    
    logger.info(f"Added {len(new_entries)} new WSJ-related entries")
    return ledger + new_entries

def _create_wsj_jonah_payment_from_config(wsj_date: date, wsj_config: Dict[str, Any]) -> LedgerRow:
    """
    Create Jonah's payment for WSJ charge based on configuration.
    """
    jonah_config = wsj_config['auto_jonah_payment']
    amount = Decimal(str(jonah_config['amount']))
    description = jonah_config['description']
    
    return _create_payment_row(
        description=description,
        payment_date=wsj_date,
        amount=amount,
        family='JJ'
    )

def _create_wsj_jonah_payment(wsj_date: date) -> LedgerRow:
    """
    Backward compatibility function - creates WSJ Jonah payment using config.
    """
    config = _load_config()
    wsj_config = config['periodic_charges']['wsj']
    return _create_wsj_jonah_payment_from_config(wsj_date, wsj_config)

def jonah_payment_for_bill(bill_rows: List[LedgerRow], due_date: date) -> LedgerRow | None:
    """
    Calculate Jonah's payment for a T-Mobile bill based on JJ family allocation.
    
    This function calculates the total amount that the JJ family owes for a T-Mobile bill
    and creates a corresponding payment entry for Jonah.
    
    Args:
        bill_rows: List of LedgerRow objects representing the T-Mobile bill entries
        due_date: The due date of the T-Mobile bill
        
    Returns:
        LedgerRow representing Jonah's payment, or None if no JJ costs found
    """
    logger.info(f"Calculating Jonah payment for T-Mobile bill due {due_date}")
    
    # Calculate total JJ costs from all bill entries
    total_jj_cost = Decimal('0')
    bill_descriptions = []
    
    for row in bill_rows:
        if row.jj and row.jj != Decimal('0'):
            total_jj_cost += row.jj
            bill_descriptions.append(row.description)
    
    if total_jj_cost == Decimal('0'):
        logger.debug("No JJ costs found in bill, no Jonah payment needed")
        return None
    
    # Create payment row (negative amount since it's a payment)
    payment_amount = -total_jj_cost
    
    logger.info(f"Jonah payment calculated: ${payment_amount} for bill due {due_date}")
    logger.debug(f"Payment covers: {', '.join(bill_descriptions[:3])}{'...' if len(bill_descriptions) > 3 else ''}")
    
    payment_row = _create_payment_row(
        description="Jonah",
        payment_date=due_date,
        amount=payment_amount,
        family='JJ'
    )
    
    return payment_row

def add_jonah_payment_if_missing(ledger: List[LedgerRow], bill_rows: List[LedgerRow], due_date: date) -> List[LedgerRow]:
    """
    Add Jonah's payment for a T-Mobile bill if it doesn't already exist in the ledger.
    
    This function checks if Jonah already has a payment on the bill due date,
    and if not, calculates and adds the appropriate payment based on JJ costs.
    
    Args:
        ledger: Current ledger entries
        bill_rows: T-Mobile bill entries that were just added
        due_date: Due date of the T-Mobile bill
        
    Returns:
        Updated ledger with Jonah payment added if needed
    """
    logger.debug(f"Checking if Jonah payment exists for {due_date}")
    
    # Check if Jonah already has a payment on this date
    existing_jonah_payments = [
        row for row in ledger 
        if row.date == due_date 
        and "jonah" in row.description.lower() 
        and row.category == "payment"
        and row.amount < 0  # payments are negative
    ]
    
    if existing_jonah_payments:
        logger.debug(f"Jonah payment already exists for {due_date}: {existing_jonah_payments[0].description}")
        return ledger
    
    # Calculate and add Jonah's payment
    jonah_payment = jonah_payment_for_bill(bill_rows, due_date)
    
    if jonah_payment:
        logger.info(f"Adding Jonah payment for {due_date}: {jonah_payment.amount}")
        return ledger + [jonah_payment]
    else:
        logger.debug(f"No Jonah payment needed for {due_date}")
        return ledger

def update_all_scheduled(ledger: List[LedgerRow]) -> List[LedgerRow]:
    """
    Apply all scheduled payment and expense rules to bring the ledger up to date.
    
    This is a convenience function that applies all the individual schedule functions
    in the correct order.
    
    Note: This does NOT include Jonah payments, as those are calculated when
    T-Mobile bills are processed in the allocator.
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