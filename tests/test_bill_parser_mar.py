

"""
Tests for parsing the March 2025 T‑Mobile bill.

These tests complement the April suite and focus on mid‑cycle plan changes,
11 voice lines, three wearables (one newly added with a prorated $20.66
charge), zero net connected‑device charges, and no international usage.
"""
from decimal import Decimal
from datetime import date
from pathlib import Path

import pytest

from family_mobile_ledger import bill_parser


# --------------------------------------------------------------------------- #
# Helpers / fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def march_pdf() -> Path:
    pdf_path = Path("/Users/jonaheaton/Documents/family_mobile_ledger/SummaryBillMar2025.pdf")
    assert pdf_path.exists(), f"Fixture PDF not found at {pdf_path}"
    return pdf_path


# --------------------------------------------------------------------------- #
# Basic headline numbers
# --------------------------------------------------------------------------- #
def test_parse_basic_totals_mar(march_pdf):
    bill = bill_parser.parse_bill(march_pdf)

    # ----- headline numbers -----
    assert bill.due_date == date(2025, 3, 24)
    assert bill.total_due == Decimal("393.59")

    # ----- plan subtotals -------
    # From the PLANS banner: 11 VOICE LINES = $260.00 | 1 CONNECTED DEVICE = $0.00 | 3 WEARABLES = $54.66
    assert bill.voice_subtotal == Decimal("260.00")
    assert bill.connected_subtotal == Decimal("0.00")
    assert bill.wearable_subtotal == Decimal("54.66")

    # Services / Netflix
    assert bill.netflix_charge == Decimal("11.00")


# --------------------------------------------------------------------------- #
# Billing cycle window
# --------------------------------------------------------------------------- #
def test_cycle_dates_mar(march_pdf):
    bill = bill_parser.parse_bill(march_pdf)

    # Regular charges explicitly state Mar 04 – Apr 03
    assert bill.cycle_start == date(2025, 3, 4)
    assert bill.cycle_end == date(2025, 4, 3)
    assert bill.cycle_end > bill.cycle_start


# --------------------------------------------------------------------------- #
# Equipment parsing (four devices; one is a $0.00 promo watch)
# --------------------------------------------------------------------------- #
def test_equipment_parsing_mar(march_pdf):
    bill = bill_parser.parse_bill(march_pdf)

    expected = {
        "4102272625": Decimal("33.34"),
        "2022586292": Decimal("26.25"),
        "3476366212": Decimal("8.34"),
        "8573403847": Decimal("0.00"),  # new watch with fully credited installment
    }
    assert bill.equipments == expected
    assert sum(bill.equipments.values()) == Decimal("67.93")


# --------------------------------------------------------------------------- #
# Usage / one‑time charges
# --------------------------------------------------------------------------- #
def test_usage_parsing_mar(march_pdf):
    bill = bill_parser.parse_bill(march_pdf)

    # March has **no** international/roaming usage charges.
    assert bill.usage == {}
    assert sum(bill.usage.values(), Decimal("0")) == Decimal("0")


# --------------------------------------------------------------------------- #
# Voice‑line count sanity check (11 reported → 10 billable after line transfers)
# --------------------------------------------------------------------------- #
def test_voice_line_count_sanity_mar(march_pdf):
    bill = bill_parser.parse_bill(march_pdf)

    # Header states 11 voice lines, but line 2409883906 is "Old number" and non-billable
    # System should detect this and use 10 billable lines for allocation
    assert bill.voice_line_count == 10, f"Expected 10 billable lines after line transfer detection, got {bill.voice_line_count}"
    assert bill.voice_subtotal == Decimal("260.00")
    
    # Per-line rate should be based on 10 billable lines: $260/10 = $26.00
    per_line = bill.voice_subtotal / Decimal(bill.voice_line_count)
    assert per_line == Decimal("26.00")


# --------------------------------------------------------------------------- #
# Line transfer detection test (March has "Old number" line 2409883906)
# --------------------------------------------------------------------------- #  
def test_line_transfer_detection_mar(march_pdf):
    """Test detection of non-allocatable voice lines during line transfers."""
    bill = bill_parser.parse_bill(march_pdf)
    
    # March bill has line transfer scenario:
    # - Top level reports: "11 VOICE LINES = $260.00"
    # - Bill summary shows line (240) 988-3906 as "Old number" with null Plans column  
    # - Only 10 lines should be billable/allocatable
    
    # System should automatically detect and exclude non-allocatable line
    assert bill.voice_line_count == 10
    assert bill.voice_subtotal == Decimal("260.00")
    
    # Verify that cost allocation will be based on 10 lines, not 11
    expected_cost_per_line = Decimal("260.00") / Decimal("10")  # $26.00
    assert expected_cost_per_line == Decimal("26.00")


# --------------------------------------------------------------------------- #
# Mid‑cycle changes sanity: connected device nets to $0; wearables include $20.66 new line
# --------------------------------------------------------------------------- #
def test_midcycle_changes_net_zero_connected_mar(march_pdf):
    bill = bill_parser.parse_bill(march_pdf)

    # Connected device shows +$1.83 and -$1.83 mid‑cycle → net $0.00 in PLANS.
    assert bill.connected_subtotal == Decimal("0.00")

    # Wearables subtotal includes regular $17 + $17 plus a prorated $20.66 new wearable = $54.66
    assert bill.wearable_subtotal == Decimal("54.66")