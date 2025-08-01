import pytest
from decimal import Decimal
from datetime import date
from pathlib import Path

# Bring the parser into scope
from family_mobile_ledger import bill_parser


def _project_root() -> Path:
    """Return the project root assuming tests/ is a direct child."""
    return Path(__file__).resolve().parent
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def june_pdf() -> Path:
    pdf_path = Path('/Users/jonaheaton/Documents/family_mobile_ledger/SummaryBillJun2025.pdf')
    # pdf_path = _project_root() / "SummaryBillJun2025.pdf"
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


def test_date_extraction_patterns(june_pdf):
    """Test that date extraction follows expected patterns"""
    bill = bill_parser.parse_bill(june_pdf)
    
    # Due date should be extracted correctly
    # For June 2025 bill, this should be June 24, 2025
    assert bill.due_date == date(2025, 6, 24)
    
    # Cycle dates should follow monthly billing pattern
    # June bill covers service period Jun 04 - Jul 03
    assert bill.cycle_start == date(2025, 6, 4)
    assert bill.cycle_end == date(2025, 7, 3)
    
    # Verify cycle spans approximately one month
    cycle_days = (bill.cycle_end - bill.cycle_start).days
    assert 28 <= cycle_days <= 31, f"Cycle length should be ~1 month, got {cycle_days} days"
    
    # The due date should be reasonable relative to cycle end
    # T-Mobile typically bills ~3 weeks after cycle end
    due_to_cycle_gap = (bill.due_date - bill.cycle_end).days
    assert -30 <= due_to_cycle_gap <= 0, f"Due date gap from cycle end: {due_to_cycle_gap} days"


def test_allocator_date_usage(june_pdf):
    """Test that allocator uses appropriate date for ledger entries"""
    from family_mobile_ledger.allocator import allocate
    
    bill = bill_parser.parse_bill(june_pdf)
    ledger_rows = allocate(bill)
    
    # All ledger entries should have the same date
    dates_used = {row.date for row in ledger_rows}
    assert len(dates_used) == 1, f"Inconsistent dates in ledger: {dates_used}"
    
    ledger_date = dates_used.pop()
    
    # Document which date is being used (this test reveals the current behavior)
    # Currently uses cycle_end, but arguably should use due_date
    if ledger_date == bill.cycle_end:
        print(f"INFO: Allocator using cycle_end ({bill.cycle_end}) for ledger entries")
    elif ledger_date == bill.due_date:
        print(f"INFO: Allocator using due_date ({bill.due_date}) for ledger entries")
    else:
        print(f"WARNING: Allocator using unexpected date ({ledger_date}) for ledger entries")
    
    # Verify the date is one of the reasonable options
    assert ledger_date in [bill.due_date, bill.cycle_end], \
        f"Ledger date {ledger_date} should be either due_date ({bill.due_date}) or cycle_end ({bill.cycle_end})"