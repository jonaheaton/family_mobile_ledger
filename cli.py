import click
from pathlib import Path
from family_mobile_ledger import bill_parser, allocator, ledger_updater

DEFAULT_LEDGER_LOCATION = Path('expenses.csv')

@click.command()
@click.option('--ledger-csv', type=click.Path(path_type=Path), default=DEFAULT_LEDGER_LOCATION, help='Path to the ledger CSV file')
@click.argument('pdfs', nargs=-1, type=click.Path(exists=True, path_type=Path))
def main(ledger_csv, pdfs):
    for pdf in pdfs:
        bill = bill_parser.parse_bill(pdf)
        rows = allocator.allocate(bill)
        ledger_updater.append_rows(ledger_csv, rows)
        click.echo(f'✔ {pdf.name} → {len(rows)} rows appended')

if __name__ == '__main__':
    main()