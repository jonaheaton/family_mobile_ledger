import pytest
from decimal import Decimal
from datetime import date
from pathlib import Path

# Bring the parser into scope
from family_mobile_ledger import bill_parser


def _project_root() -> Path:
    """Return the project root assuming tests/ is a direct child."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def june_pdf() -> Path:
    pdf_path = _project_root() / "SummaryBillJun2025.pdf"
    assert pdf_path.exists(), f"Fixture PDF not found at {pdf_path}"
    return pdf_path


def test_parse_basic_totals(june_pdf):
    bill = bill_parser.parse_bill(june_pdf)

    # ------------ headline numbers ------------
    assert bill.due_date == date(2025, 6, 24)
    assert bill.total_due == Decimal("411.59")

    # ------------ plan subtotals --------------
    assert bill.voice_subtotal == Decimal("280.00")
    assert bill.wearable_subtotal == Decimal("54.00")
    # There is no connected‑device plan this month
    assert bill.connected_subtotal == Decimal("0.00")
    assert bill.netflix_charge == Decimal("18.00")

    # ------------ equipment -------------------
    # Three devices this cycle with a net total that matches the PDF
    # assert len(bill.equipments) == 3
    assert sum(bill.equipments.values()) == Decimal("59.59")

    # Spot‑check each device’s parsed amount
    assert bill.equipments.get("4102272625") == Decimal("33.34")
    assert bill.equipments.get("2022586292") == Decimal("26.25")
    assert bill.equipments.get("8573403847") == Decimal("0.00")

    # ------------ usage charges ---------------
    # June 2025 bill has no INTL / roaming usage lines
    assert bill.usage == {}


def test_cycle_dates(june_pdf):
    bill = bill_parser.parse_bill(june_pdf)

    # Cycle window appears as "Jun 04 - Jul 03" (see page 2),
    # so start = 2025‑06‑04, end = 2025‑07‑03
    assert bill.cycle_start == date(2025, 6, 4)
    assert bill.cycle_end == date(2025, 7, 3)

    # Sanity check: cycle_end must be after cycle_start
    assert bill.cycle_end > bill.cycle_start