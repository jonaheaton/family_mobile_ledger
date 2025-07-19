import pandas as pd
from pathlib import Path
from .datatypes import LedgerRow

COLUMNS = ['Date Due', 'Description', 'JJ', 'KS', 'DJ', 'RE']

def append_rows(csv_path: Path, rows: list[LedgerRow]) -> None:
    df_old = pd.read_csv(csv_path, parse_dates=['Date Due'])
    df_new = pd.DataFrame([r.__dict__ for r in rows])
    df_new = df_new.rename(columns={'jj':'JJ','ks':'KS','dj':'DJ','re':'RE'})
    df_combined = pd.concat([df_old, df_new], ignore_index=True)
    df_combined[COLUMNS].to_csv(csv_path, index=False)