# family_mobile_ledger

Automates month-to-month cost sharing for our extended-family T-Mobile plan.  
Given **(1)** the working expense ledger CSV and **(2)** one or more T-Mobile
summary-bill PDFs, it:

1. Parses each bill and extracts the subtotals, equipment payments, Netflix,
   and one-time usage charges.
2. Allocates every cost line to the correct family using explicit rules
   (Voice, Wearables, Connected, Equipment, Netflix, Usage).
3. Appends the new rows to the ledger CSV and inserts an AutoPay row so the
   running balance stays correct.
4. Leaves reimbursement rows untouched so we can still track who has paid
   Jonah back.

---

## 📁 Project structure

```text
family_mobile_ledger/
├── __init__.py
├── cli.py               # single command‐line entry point
├── config.py            # loads family_config.yaml helpers
├── datatypes.py         # small @dataclass models (Device, BillTotals …)
├── bill_parser.py       # text-mines a PDF into BillTotals
├── allocator.py         # implements Rules A-F, builds LedgerRow list
├── ledger_updater.py    # merges rows into the CSV
├── io_utils.py          # (future) common I/O helpers
├── data/
│   └── family_config.yaml  # mapping of phone → family, adult counts, prefs
└── tests/               # pytest modules exercising each layer
    ├── test_bill_parser.py  # tests the bill_parser
    └── test_allocator.py     # tests the allocator rules
```

## ⏳ Allocation rules

| Rule | Category | Allocation logic |
|------|----------|------------------|
| **A** | **Voice plan subtotal** | Divide the bill’s voice‑line subtotal by the count of **active, non‑“Removed”** voice lines. Charge each family the per‑line rate multiplied by how many voice lines they own that month. |
| **B** | **Wearable plan subtotal** | Pass through the exact monthly fee for each wearable line to its owning family. *(A future flag will let us pool or pro‑rate these.)* |
| **C** | **Connected‑device / Mobile‑Internet plans** | Pass through the exact monthly fee to the owning family. |
| **D** | **Equipment installments & promo credits** | For each device, sum **all** Equipment rows (positive installments plus negative promo credits) for that cycle; charge the resulting net amount to that family. |
| **E** | **Netflix subscription** | Split proportionally by the **number of adults** in each family. As of 2025 every family has two adults, so the charge is an even ¼ split. |
| **F** | **One‑time usage charges** | Aggregate all international calling / roaming usage per phone number and charge 100 % of it to that phone’s family. |
| **Precision & rounding** | – | Keep full‑precision `Decimal` values during calculations. Round to two decimals when writing ledger rows. If rounding introduces a penny drift from any bill subtotal, adjust the final family’s share by that penny so the row matches the bill exactly. |

## 🛠 Installation

```bash
# create and activate conda env
conda env create -f environment.yml
conda activate family_ledger
# (or) conda create -n family_ledger -c conda-forge python=3.11 \
#        pdfplumber click pyyaml pandas

pip install -e .    # optional editable install for `python -m ...
```

## 🚀 Quick start

```bash
# Append Feb 2025 bill rows into the existing CSV
python -m family_mobile_ledger.cli \
    /path/to/T-Mobile_Family_Expenses.csv \
    /path/to/SummaryBillFeb2025.pdf
```

## 🔧 To‑do

A road‑map of next iterations, with concrete implementation notes.

| Priority | Task | Detailed steps |
|----------|------|----------------|
| 🌟 | **Harden `bill_parser.py`** | • Replace placeholder regexes with deterministic, multi‑line patterns or table parsing using `pdfplumber`’s extracted `page.extract_table()`; • Add unit fixtures: save trimmed text from Dec/Jan/Feb 2025 bills in `tests/fixtures/` and write tests that assert each subtotal, equipment amount, and usage record; • Refactor parsing into helper functions (`_parse_subtotals`, `_parse_equipment`, `_parse_usage`) so they can be unit‑tested in isolation. |
| 🌟 | **Penny‑adjust rounding** | • After `allocator.allocate` builds per‑category buckets, sum the *rounded* values and compare to the source subtotal; • If off by ≥ ¥0.01, bump the family with the largest share (ties → JJ) by the missing penny (<https://en.wikipedia.org/wiki/Bankers_rounding>); • Unit‑test with crafted amounts that round .005 up/down. |
| 🌟 | **Wearable/Connected strategy flag** | • Extend `family_config.yaml` with;   ```yaml\n  plan_split:\n    wearables: pass_through  # or pooled\n    connected: pass_through\n  ```; • Refactor allocator to branch on that flag; • Add tests for each strategy. |
| ⭐ | **CLI duplicate‑month guard** | • In `ledger_updater.append_rows`, check if a row with the same `Description` already exists; if so, abort unless `--force` is provided; • Emit a colored warning via `click.secho`. |
| ⭐ | **Balance summary report** | • After updating the CSV, calculate per‑family column sums and print a table (or write `balances_YYYY‑MM.html`); • Consider using `tabulate` for pretty CLI output. |
| ⭐ | **Bank‑CSV ingestion (reimbursements)** | • Design a simple matcher: rows where `Description` contains “T‑Mobile Zelle” and an amount matching a known family share → create negative row in that family’s column; • Prototype with February checking CSV; add flag `--payments bank.csv`. |
| 🔹 | **CI & lint** | • Add GitHub Actions workflow: matrix on `python‑version: [3.11]` → `pytest -q` and `ruff check .`; • Fail build if coverage < 80 %. |
| 🔹 | **Docker image** | • Create `Dockerfile` based on `python:3.11-slim`, copy code, run `pip install -r requirements.txt`; • Entry‑point `CMD ["family-mobile-ledger", "--help"]`. |
| 🔹 | **Extended docs** | • Split README into **Usage**, **Developer guide**, **Contributing** in `docs/` folder; • Add architecture diagram (draw.io PNG) and link from README. |
