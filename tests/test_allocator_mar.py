"""
Allocator tests for the **March 2025** bill with line transfer complexity.

March 2025 presents a unique line transfer scenario:
- Top-level: "11 VOICE LINES = $260.00"
- Reality: Only 10 lines are billable (line 2409883906 is "Old number" with null Plans)
- System should detect this, warn user, and allocate based on 10 billable lines

This validates that the enhanced bill parser and allocator correctly handle
line transfer edge cases without allocation mismatches.
"""
from decimal import Decimal
from datetime import date
from pathlib import Path

import pytest

from family_mobile_ledger import allocator, bill_parser
from family_mobile_ledger.datatypes import BillTotals


@pytest.fixture()
def march_bill() -> BillTotals:
    """Parse the March 2025 bill with line transfer complexity."""
    pdf_path = Path("SummaryBillMar2025.pdf")
    return bill_parser.parse_bill(pdf_path)


def test_march_voice_allocation_with_line_transfer(march_bill):
    """Test that voice allocation works correctly despite line transfer complexity."""
    rows = allocator.allocate(march_bill)
    
    # Find voice line allocation row
    voice_row = None
    for row in rows:
        if "voice lines" in row.description:
            voice_row = row
            break
    
    assert voice_row is not None, "Voice line allocation row not found"
    
    # Should allocate $260 across 10 billable lines ($26/line)
    # Based on family config: JJ=2 lines, KS=5 lines, DJ=1 line, RE=2 lines  
    expected_allocations = {
        "JJ": Decimal("52.00"),   # 2 lines × $26 = $52
        "KS": Decimal("130.00"),  # 5 lines × $26 = $130  
        "DJ": Decimal("26.00"),   # 1 line × $26 = $26
        "RE": Decimal("52.00")    # 2 lines × $26 = $52
    }
    
    assert voice_row.jj == expected_allocations["JJ"]
    assert voice_row.ks == expected_allocations["KS"] 
    assert voice_row.dj == expected_allocations["DJ"]
    assert voice_row.re == expected_allocations["RE"]
    
    # Verify shares are correct (10 total billable lines)
    assert voice_row.shares_jj == 2
    assert voice_row.shares_ks == 5  
    assert voice_row.shares_dj == 1
    assert voice_row.shares_re == 2
    assert voice_row.shares_total == 10
    
    # Total should equal voice subtotal
    total_allocated = voice_row.jj + voice_row.ks + voice_row.dj + voice_row.re
    assert total_allocated == march_bill.voice_subtotal


def test_march_allocation_total_validation_no_mismatch(march_bill, capsys):
    """Test that March bill doesn't trigger allocation mismatch warnings after line transfer handling."""
    # March bill should not trigger any allocation mismatch warnings
    # because the line transfer detection correctly handles the discrepancy
    rows = allocator.allocate(march_bill)
    
    captured = capsys.readouterr()
    assert "🚨 WARNING: ALLOCATION MISMATCH DETECTED!" not in captured.out
    
    # Verify total allocation matches bill total
    total_allocated = sum(row.amount for row in rows)
    assert abs(total_allocated - march_bill.total_due) <= Decimal('0.01')


def test_march_equipment_allocation(march_bill):
    """Test equipment allocation for March 2025 devices."""
    rows = allocator.allocate(march_bill)
    
    # Find all equipment rows
    equipment_rows = [row for row in rows if row.category == 'equipment']
    
    # Expected equipment allocations based on device ownership
    expected_equipment = {
        "jonah iphone": (Decimal("33.34"), "JJ"),      # 4102272625 → JJ
        "rebecca iphone": (Decimal("26.25"), "RE"),    # 2022586292 → RE  
        "julia apple watch": (Decimal("8.34"), "RE"),  # 3476366212 → RE
        # 8573403847 → $0.00 so might not create a row
    }
    
    # Verify each expected device has correct allocation
    for expected_desc, (expected_amount, expected_family) in expected_equipment.items():
        matching_rows = [row for row in equipment_rows if expected_desc in row.description.lower()]
        if expected_amount > 0:
            assert len(matching_rows) == 1, f"Expected exactly one row for {expected_desc}"
            row = matching_rows[0]
            assert row.amount == expected_amount
            # Verify allocation goes to correct family
            family_costs = {"JJ": row.jj, "KS": row.ks, "DJ": row.dj, "RE": row.re}
            assert family_costs[expected_family] == expected_amount
            # Verify other families get $0
            for family, cost in family_costs.items():
                if family != expected_family:
                    assert cost == Decimal("0.00")


def test_march_line_transfer_warnings_displayed(march_bill, capsys):
    """Test that line transfer warnings are properly displayed."""
    # Parse the bill (warnings come from bill parser)
    bill_parser.parse_bill(Path("SummaryBillMar2025.pdf"))
    
    captured = capsys.readouterr()
    
    # Should see transfer detection warnings
    assert "⚠️  VOICE LINE TRANSFER DETECTED:" in captured.out
    assert "Total voice lines reported: 11" in captured.out
    assert "Non-allocatable lines (transfers/old numbers): 1" in captured.out
    assert "2409883906 - Non-billable voice line (Old number)" in captured.out
    assert "Billable voice lines for allocation: 10" in captured.out
    assert "Using billable count for cost allocation calculations." in captured.out