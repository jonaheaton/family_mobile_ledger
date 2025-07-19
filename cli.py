import click
from pathlib import Path
from family_mobile_ledger import bill_parser, allocator, ledger_updater

@click.command()
@click.argument('ledger_csv', type=click.Path(exists=True, path_type=Path))
@click.argument('pdfs', nargs=-1, type=click.Path(exists=True, path_type=Path))
def main(ledger_csv, pdfs):
    for pdf in pdfs:
        bill = bill_parser.parse_bill(pdf)
        rows = allocator.allocate(bill)
        ledger_updater.append_rows(ledger_csv, rows)
        click.echo(f'✔ {pdf.name} → {len(rows)} rows appended')

if __name__ == '__main__':
    main()