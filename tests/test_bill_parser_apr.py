
# %%
"""
Tests for parsing the April 2025 T‑Mobile bill.

These tests *extend* (do not replace) the June‑bill tests that already live in
`test_bill_parser.py`.  They focus on edge‑cases that appear for the first time
in April 2025: a zero‑dollar equipment installment, international usage
charges, three wearables, and a 10‑line voice plan.
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
def april_pdf() -> Path:
    pdf_path = Path('/Users/jonaheaton/Documents/family_mobile_ledger/SummaryBillApr2025.pdf')
    # pdf_path = _project_root() / "SummaryBillApr2025.pdf"
    print(f"Using fixture PDF at {pdf_path}")
    assert pdf_path.exists(), f"Fixture PDF not found at {pdf_path}"
    return pdf_path


# --------------------------------------------------------------------------- #
# Basic headline numbers
# --------------------------------------------------------------------------- #
def test_parse_basic_totals_apr(april_pdf):
    bill = bill_parser.parse_bill(april_pdf)

    # ----- headline numbers -----
    assert bill.due_date == date(2025, 4, 24)
    assert bill.total_due == Decimal("567.65")

    # ----- plan subtotals -------
    assert bill.voice_subtotal == Decimal("280.00")
    assert bill.wearable_subtotal == Decimal("54.00")
    assert bill.connected_subtotal == Decimal("0.00")  # hotspot paused this month
    assert bill.netflix_charge == Decimal("18.00")


# --------------------------------------------------------------------------- #
# Billing cycle window
# --------------------------------------------------------------------------- #
def test_cycle_dates_apr(april_pdf):
    bill = bill_parser.parse_bill(april_pdf)

    assert bill.cycle_start == date(2025, 4, 4)
    assert bill.cycle_end == date(2025, 5, 3)
    # Sanity: end date falls after start date
    assert bill.cycle_end > bill.cycle_start


# --------------------------------------------------------------------------- #
# Equipment parsing (includes a zero‑dollar promo device)
# --------------------------------------------------------------------------- #
def test_equipment_parsing_apr(april_pdf):
    bill = bill_parser.parse_bill(april_pdf)

    # Expected four devices with these net amounts
    expected = {
        "4102272625": Decimal("33.34"),
        "2022586292": Decimal("26.25"),
        "3476366212": Decimal("8.34"),
        "8573403847": Decimal("0.00"),  # fully‑credited watch
    }

    assert bill.equipments == expected
    # Sum sanity check
    assert sum(bill.equipments.values()) == Decimal("67.93")


# --------------------------------------------------------------------------- #
# Usage / international charges
# --------------------------------------------------------------------------- #
def test_usage_parsing_apr(april_pdf):
    bill = bill_parser.parse_bill(april_pdf)

    expected_usage = {
        "2405844111": Decimal("21.00"),
        "2409885184": Decimal("45.00"),
    }

    assert bill.usage == expected_usage
    assert sum(bill.usage.values()) == Decimal("66.00")


# --------------------------------------------------------------------------- #
# Voice‑line count sanity check
# --------------------------------------------------------------------------- #
def test_voice_line_count_sanity_apr(april_pdf):
    """
    Given the bill's voice subtotal of $280.00 and the known per‑line plan
    pricing of $28.00, there should be ten active voice lines this cycle.
    """
    bill = bill_parser.parse_bill(april_pdf)
    per_line = Decimal("28.00")
    assert bill.voice_subtotal == per_line * 10