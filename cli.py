'''
To Run:
python -m family_mobile_ledger.cli SummaryBillXXX2025.pdf
'''
import click
import logging
from pathlib import Path
from decimal import Decimal
from typing import Dict, List
from family_mobile_ledger import bill_parser, allocator, ledger_updater, scheduled
from family_mobile_ledger.datatypes import LedgerRow

DEFAULT_LEDGER_LOCATION = Path('expenses.csv')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def calculate_family_balances(ledger: List[LedgerRow]) -> Dict[str, Decimal]:
    """
    Calculate outstanding balance for each family.
    
    Positive balance = family owes money (charges > payments)
    Negative balance = family has credit (payments > charges)
    
    Returns:
        Dict mapping family codes to their outstanding balances
    """
    family_balances = {
        'JJ': Decimal('0'),
        'KS': Decimal('0'), 
        'DJ': Decimal('0'),
        'RE': Decimal('0')
    }
    
    for row in ledger:
        # Add family costs (positive = they owe)
        family_balances['JJ'] += row.jj
        family_balances['KS'] += row.ks
        family_balances['DJ'] += row.dj
        family_balances['RE'] += row.re
    
    return family_balances

def format_balance_report(balances: Dict[str, Decimal]) -> str:
    """
    Format family balances in an email-friendly format.
    """
    family_names = {
        'JJ': 'Jonah & Janet',
        'KS': 'Karen & Seth', 
        'DJ': 'Daniel & Jackie',
        'RE': 'Rebecca & Enrique'
    }
    
    report_lines = []
    report_lines.append("=== FAMILY MOBILE LEDGER BALANCES ===")
    report_lines.append("")
    
    total_outstanding = Decimal('0')
    
    for family_code, balance in balances.items():
        family_name = family_names[family_code]
        
        if balance > 0:
            status = f"owes ${balance:.2f}"
            total_outstanding += balance
        elif balance < 0:
            status = f"has credit of ${abs(balance):.2f}"
        else:
            status = "balanced (${:.2f})".format(balance)
        
        report_lines.append(f"{family_name} ({family_code}): {status}")
    
    report_lines.append("")
    report_lines.append(f"Total Outstanding: ${total_outstanding:.2f}")
    report_lines.append("")
    report_lines.append("(Generated automatically by Family Mobile Ledger)")
    
    return "\n".join(report_lines)

@click.command()
@click.option('--ledger-csv', type=click.Path(path_type=Path), default=DEFAULT_LEDGER_LOCATION, help='Path to the ledger CSV file')
@click.option('--skip-scheduled', is_flag=True, help='Skip automatic scheduled payment updates')
@click.argument('pdfs', nargs=-1, type=click.Path(exists=True, path_type=Path))
def main(ledger_csv, skip_scheduled, pdfs):
    """
    Process bill PDFs and update the family mobile ledger.
    
    This command will:
    1. Update scheduled payments (unless --skip-scheduled is used)
    2. Process any provided PDF bills
    3. Add the new entries to the ledger CSV
    """
    
    # Step 1: Update scheduled payments (unless skipped)
    if not skip_scheduled:
        click.echo("📅 Updating scheduled payments...")
        
        # Read existing ledger
        existing_ledger = ledger_updater.read_ledger(ledger_csv)
        logger.info(f"Loaded {len(existing_ledger)} existing ledger entries")
        
        # Apply scheduled updates
        updated_ledger = scheduled.update_all_scheduled(existing_ledger)
        
        # Check if any new scheduled entries were added
        new_scheduled_count = len(updated_ledger) - len(existing_ledger)
        if new_scheduled_count > 0:
            # Write the updated ledger back (replacing the entire file)
            # We need to convert back to the original format and write
            ledger_updater.write_full_ledger(ledger_csv, updated_ledger)
            click.echo(f"✔ Added {new_scheduled_count} scheduled payment entries")
        else:
            click.echo("✔ All scheduled payments are up to date")
    else:
        click.echo("⏭ Skipping scheduled payment updates")
    
    # Step 2: Process PDF bills
    if pdfs:
        click.echo(f"📄 Processing {len(pdfs)} bill PDF(s)...")
        
        for pdf in pdfs:
            bill = bill_parser.parse_bill(pdf)
            bill_rows = allocator.allocate(bill)
            
            # Add the bill entries to the ledger
            ledger_updater.append_rows(ledger_csv, bill_rows)
            click.echo(f'✔ {pdf.name} → {len(bill_rows)} rows appended')
            
            # Check if we need to add Jonah's payment for this bill
            from family_mobile_ledger.scheduled import add_jonah_payment_if_missing
            
            # Read the current ledger (including the entries we just added)
            current_ledger = ledger_updater.read_ledger(ledger_csv)
            
            # Add Jonah payment if missing
            updated_ledger = add_jonah_payment_if_missing(current_ledger, bill_rows, bill.due_date)
            
            # If a Jonah payment was added, write the full ledger back
            if len(updated_ledger) > len(current_ledger):
                ledger_updater.write_full_ledger(ledger_csv, updated_ledger)
                click.echo(f'💰 Added Jonah payment for {bill.due_date}')
    else:
        click.echo("📄 No PDF bills to process")
    
    click.echo("🎉 Ledger update complete!")
    
    # Step 3: Display outstanding balances
    click.echo("\n💰 Calculating outstanding balances...")
    
    # Read the final ledger state
    final_ledger = ledger_updater.read_ledger(ledger_csv)
    balances = calculate_family_balances(final_ledger)
    balance_report = format_balance_report(balances)
    
    click.echo("\n" + balance_report)

if __name__ == '__main__':
    main()