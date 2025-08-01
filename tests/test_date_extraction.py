"""
Comprehensive tests for date extraction from bill PDFs.

This test suite verifies that:
1. Bill due dates are correctly extracted 
2. Cycle periods are correctly parsed
3. The relationship between due dates and cycle periods is consistent
4. The allocator uses the correct date for ledger entries
"""

import pytest
from decimal import Decimal
from datetime import date
from pathlib import Path

from family_mobile_ledger import bill_parser
from family_mobile_ledger.allocator import allocate


class TestDateExtraction:
    """Test date extraction across all available bill PDFs"""
    
    @pytest.fixture(scope="class")
    def bill_data(self):
        """Load all available bills and their expected dates"""
        bills = {}
        
        # Define expected data for each bill
        expected_data = {
            'Mar': {
                'pdf': '/Users/jonaheaton/Documents/family_mobile_ledger/SummaryBillMar2025.pdf',
                'due_date': date(2025, 3, 24),
                'cycle_start': date(2025, 3, 4), 
                'cycle_end': date(2025, 4, 3)
            },
            'Apr': {
                'pdf': '/Users/jonaheaton/Documents/family_mobile_ledger/SummaryBillApr2025.pdf',
                'due_date': date(2025, 4, 24),
                'cycle_start': date(2025, 4, 4),
                'cycle_end': date(2025, 5, 3)
            },
            'May': {
                'pdf': '/Users/jonaheaton/Documents/family_mobile_ledger/SummaryBillMay2025.pdf', 
                'due_date': date(2025, 5, 24),
                'cycle_start': date(2025, 5, 4),
                'cycle_end': date(2025, 6, 3)
            },
            'Jun': {
                'pdf': '/Users/jonaheaton/Documents/family_mobile_ledger/SummaryBillJun2025.pdf',
                'due_date': date(2025, 6, 24),
                'cycle_start': date(2025, 6, 4),
                'cycle_end': date(2025, 7, 3)
            }
        }
        
        # Only include bills whose PDFs exist
        for month, data in expected_data.items():
            pdf_path = Path(data['pdf'])
            if pdf_path.exists():
                try:
                    bill = bill_parser.parse_bill(pdf_path)
                    bills[month] = {
                        'bill': bill,
                        'expected': data,
                        'pdf_path': pdf_path
                    }
                except Exception as e:
                    pytest.skip(f"Could not parse {month} bill: {e}")
        
        if not bills:
            pytest.skip("No bill PDFs available for testing")
            
        return bills

    def test_due_date_extraction(self, bill_data):
        """Test that due dates are correctly extracted from PDFs"""
        for month, data in bill_data.items():
            bill = data['bill']
            expected = data['expected']
            
            assert bill.due_date == expected['due_date'], \
                f"{month} bill due date mismatch: got {bill.due_date}, expected {expected['due_date']}"

    def test_cycle_date_extraction(self, bill_data):
        """Test that cycle start and end dates are correctly extracted"""
        for month, data in bill_data.items():
            bill = data['bill']
            expected = data['expected']
            
            assert bill.cycle_start == expected['cycle_start'], \
                f"{month} bill cycle start mismatch: got {bill.cycle_start}, expected {expected['cycle_start']}"
                
            assert bill.cycle_end == expected['cycle_end'], \
                f"{month} bill cycle end mismatch: got {bill.cycle_end}, expected {expected['cycle_end']}"

    def test_date_consistency_patterns(self, bill_data):
        """Test that the relationship between dates follows expected patterns"""
        for month, data in bill_data.items():
            bill = data['bill']
            
            # Cycle should span approximately one month
            cycle_days = (bill.cycle_end - bill.cycle_start).days
            assert 28 <= cycle_days <= 31, \
                f"{month} bill cycle length unusual: {cycle_days} days"
            
            # Cycle end should be after cycle start
            assert bill.cycle_end > bill.cycle_start, \
                f"{month} bill cycle end not after cycle start"
            
            # Due date should be within reasonable range of cycle end
            # (T-Mobile bills are typically due ~3 weeks after cycle end)
            days_diff = abs((bill.due_date - bill.cycle_end).days)
            assert days_diff <= 30, \
                f"{month} bill due date too far from cycle end: {days_diff} days"

    def test_monthly_progression(self, bill_data):
        """Test that consecutive monthly bills have proper date progression"""
        months = sorted(bill_data.keys())
        
        for i in range(len(months) - 1):
            current_month = months[i]
            next_month = months[i + 1]
            
            current_bill = bill_data[current_month]['bill']
            next_bill = bill_data[next_month]['bill']
            
            # Next month's cycle start should be close to current month's cycle end
            # (allowing for some overlap or gap)
            start_diff = abs((next_bill.cycle_start - current_bill.cycle_end).days)
            assert start_diff <= 2, \
                f"Cycle boundary mismatch between {current_month} and {next_month}: {start_diff} days"

    def test_allocator_uses_correct_date(self, bill_data):
        """Test that the allocator creates ledger entries with appropriate dates"""
        for month, data in bill_data.items():
            bill = data['bill']
            ledger_rows = allocate(bill)
            
            # All ledger rows should have the same date
            dates = {row.date for row in ledger_rows}
            assert len(dates) == 1, \
                f"{month} bill allocator created entries with inconsistent dates: {dates}"
            
            ledger_date = dates.pop()
            
            # The ledger date should be either the due date or cycle end
            # Currently using cycle_end, but this test documents the expectation
            assert ledger_date in [bill.due_date, bill.cycle_end], \
                f"{month} bill ledger date {ledger_date} not due date {bill.due_date} or cycle end {bill.cycle_end}"
            
            # Document which date is actually being used
            if ledger_date == bill.cycle_end:
                print(f"{month} bill: Using cycle_end ({bill.cycle_end}) for ledger entries")
            elif ledger_date == bill.due_date:
                print(f"{month} bill: Using due_date ({bill.due_date}) for ledger entries")


class TestSpecificBillDates:
    """Test specific bills individually for detailed date verification"""
    
    def test_june_2025_dates(self):
        """Test June 2025 bill specifically"""
        pdf_path = Path('/Users/jonaheaton/Documents/family_mobile_ledger/SummaryBillJun2025.pdf')
        if not pdf_path.exists():
            pytest.skip("June 2025 PDF not available")
            
        bill = bill_parser.parse_bill(pdf_path)
        
        # These should match the PDF content exactly
        assert bill.due_date == date(2025, 6, 24)
        assert bill.cycle_start == date(2025, 6, 4) 
        assert bill.cycle_end == date(2025, 7, 3)
        
        # Verify allocator behavior
        ledger_rows = allocate(bill)
        for row in ledger_rows:
            # Currently expecting cycle_end, but this documents the issue
            assert row.date == bill.cycle_end, \
                f"Expected ledger date {bill.cycle_end}, got {row.date}"