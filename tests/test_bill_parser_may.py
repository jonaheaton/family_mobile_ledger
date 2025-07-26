

"""
Tests for parsing the May 2025 T‑Mobile bill.

Patterned after the April suite. May introduces:
- 10 voice lines at a flat $280.00 (⇒ $28.00 per line)
- 3 wearables totaling $54.00 with mixed pricing ($17, $17, $20)
- No connected‑device charge this month ($0.00)
- Four equipment items with a final $8.18 watch installment
- No international/roaming usage charges
"""
from decimal import Decimal
from datetime import date
from pathlib import Path

import pytest

from family_mobile_ledger import bill_parser


# --------------------------------------------------------------------------- #
# Fixture
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def may_pdf() -> Path:
    pdf_path = Path("/Users/jonaheaton/Documents/family_mobile_ledger/SummaryBillMay2025.pdf")
    assert pdf_path.exists(), f"Fixture PDF not found at {pdf_path}"
    return pdf_path


# --------------------------------------------------------------------------- #
# Basic headline numbers and plan subtotals
# --------------------------------------------------------------------------- #
def test_parse_basic_totals_may(may_pdf):
    bill = bill_parser.parse_bill(may_pdf)

    # Headline
    assert bill.due_date == date(2025, 5, 24)
    assert bill.total_due == Decimal("419.77")

    # PLANS banner: 10 VOICE LINES = $280.00 | 3 WEARABLES = $54.00
    assert bill.voice_subtotal == Decimal("280.00")
    assert bill.wearable_subtotal == Decimal("54.00")
    assert bill.connected_subtotal == Decimal("0.00")

    # THIS BILL SUMMARY shows Services / Netflix = $18.00
    assert bill.netflix_charge == Decimal("18.00")


# --------------------------------------------------------------------------- #
# Cycle window
# --------------------------------------------------------------------------- #
def test_cycle_dates_may(may_pdf):
    bill = bill_parser.parse_bill(may_pdf)
    # "REGULAR CHARGES May 04 - Jun 03" and "Charged in advance for bill period May 04 - Jun 03"
    assert bill.cycle_start == date(2025, 5, 4)
    assert bill.cycle_end == date(2025, 6, 3)
    assert bill.cycle_end > bill.cycle_start


# --------------------------------------------------------------------------- #
# Equipment parsing (four devices)
# --------------------------------------------------------------------------- #
def test_equipment_parsing_may(may_pdf):
    bill = bill_parser.parse_bill(may_pdf)

    expected = {
        "4102272625": Decimal("33.34"),
        "2022586292": Decimal("26.25"),
        "3476366212": Decimal("8.18"),  # final installment 24/24
        "8573403847": Decimal("0.00"),  # fully credited watch
    }
    assert bill.equipments == expected
    assert sum(bill.equipments.values()) == Decimal("67.77")


# --------------------------------------------------------------------------- #
# Usage / one‑time charges
# --------------------------------------------------------------------------- #
def test_usage_parsing_may(may_pdf):
    bill = bill_parser.parse_bill(may_pdf)

    # May has no international/roaming usage charges
    assert bill.usage == {}
    assert sum(bill.usage.values(), Decimal("0")) == Decimal("0")


# --------------------------------------------------------------------------- #
# Voice‑line count sanity (10 lines → $280 total)
# --------------------------------------------------------------------------- #
def test_voice_line_count_sanity_may(may_pdf):
    bill = bill_parser.parse_bill(may_pdf)

    per_line = Decimal("28.00")
    assert bill.voice_subtotal == per_line * 10


# --------------------------------------------------------------------------- #
# Cross‑check: plan, equipment, services totals reconcile to TOTAL DUE
# --------------------------------------------------------------------------- #
def test_totals_reconcile_to_total_due_may(may_pdf):
    bill = bill_parser.parse_bill(may_pdf)

    plans = bill.voice_subtotal + bill.wearable_subtotal + bill.connected_subtotal
    equipment = sum(bill.equipments.values())
    usage = sum(bill.usage.values(), Decimal("0"))
    services = bill.netflix_charge

    assert plans == Decimal("334.00")  # 280 + 54 + 0
    assert equipment == Decimal("67.77")
    assert services == Decimal("18.00")

    computed_total = plans + equipment + services + usage
    assert computed_total == bill.total_due == Decimal("419.77")


# --------------------------------------------------------------------------- #
# Sanity: wearable mix ($17 + $17 + $20) equals the subtotal
# --------------------------------------------------------------------------- #
def test_wearable_mix_matches_subtotal_may(may_pdf):
    bill = bill_parser.parse_bill(may_pdf)
    expected = Decimal("17.00") * 2 + Decimal("20.00")
    assert bill.wearable_subtotal == expected == Decimal("54.00")