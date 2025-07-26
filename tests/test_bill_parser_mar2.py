

"""
Tests for parsing the **March 2025** T‑Mobile bill.

This file complements `test_bill_parser.py` (June) and
`test_bill_parser_apr.py` (April) so that the parser is exercised against three
consecutive cycles with different edge‑cases:

* plan change credits / debits (mid‑cycle changes)
* 11 voice lines (the highest so far)
* 3 wearables with non‑uniform plan fees ($17 / $17 / $20.66 → rounded $54.66)
* Netflix Standard discounted to **$11.00**
* No international usage charges this month
"""
from decimal import Decimal
from datetime import date
from pathlib import Path

import pytest

from family_mobile_ledger import bill_parser


# --------------------------------------------------------------------------- #
# Helpers / fixtures
# --------------------------------------------------------------------------- #
def _project_root() -> Path:
    """Return the project root assuming tests/ is a direct child."""
    return Path(__file__).resolve().parent
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def march_pdf() -> Path:
    pdf_path = Path('/Users/jonaheaton/Documents/family_mobile_ledger/SummaryBillMar2025.pdf')
    # pdf_path = _project_root() / "SummaryBillMar2025.pdf"
    assert pdf_path.exists(), f"Fixture PDF not found at {pdf_path}"
    return pdf_path


# --------------------------------------------------------------------------- #
# Basic headline numbers
# --------------------------------------------------------------------------- #
def test_parse_basic_totals_mar(march_pdf):
    bill = bill_parser.parse_bill(march_pdf)

    # ------------ headline numbers ------------
    assert bill.due_date == date(2025, 3, 24)
    assert bill.total_due == Decimal("393.59")

    # ------------ plan subtotals --------------
    # From page‑1 PLANS banner
    assert bill.voice_subtotal == Decimal("260.00")        # 11 voice lines
    assert bill.wearable_subtotal == Decimal("54.66")      # 3 wearables
    # Connected hotspot is paused/removed this month
    assert bill.connected_subtotal == Decimal("0.00")
    # Netflix Standard discounted to $11.00
    assert bill.netflix_charge == Decimal("11.00")


# --------------------------------------------------------------------------- #
# Billing cycle window
# --------------------------------------------------------------------------- #
def test_cycle_dates_mar(march_pdf):
    bill = bill_parser.parse_bill(march_pdf)

    # Regular cycle is Mar‑04 – Apr‑03 (see page‑3 "REGULAR CHARGES")
    assert bill.cycle_start == date(2025, 3, 4)
    assert bill.cycle_end == date(2025, 4, 3)
    assert bill.cycle_end > bill.cycle_start


# --------------------------------------------------------------------------- #
# Equipment parsing (includes a zero‑dollar watch)
# --------------------------------------------------------------------------- #
def test_equipment_parsing_mar(march_pdf):
    bill = bill_parser.parse_bill(march_pdf)

    expected = {
        "4102272625": Decimal("33.34"),  # Jonah iPhone 15 Pro (trade‑in credit)
        "2022586292": Decimal("26.25"),  # Rebecca iPhone 13 mini
        "3476366212": Decimal("8.34"),   # Julia stand‑alone watch
        "8573403847": Decimal("0.00"),   # New paired watch fully promo‑credited
    }

    assert bill.equipments == expected
    assert sum(bill.equipments.values()) == Decimal("67.93")


# --------------------------------------------------------------------------- #
# Usage / international charges
# --------------------------------------------------------------------------- #
def test_usage_parsing_mar(march_pdf):
    bill = bill_parser.parse_bill(march_pdf)

    # March 2025 bill has **no** INTL / roaming usage lines
    assert bill.usage == {}