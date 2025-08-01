"""
Tests for scheduled payment and expense functions.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from family_mobile_ledger.scheduled import (
    enrique_payment, daniel_payment, seth_payment, wsj_charge,
    update_all_scheduled, _get_existing_entries
)
from family_mobile_ledger.datatypes import LedgerRow


class TestScheduledPayments:
    """Test scheduled payment functions"""
    
    def test_enrique_payment_empty_ledger(self):
        """Test Enrique payment generation with empty ledger"""
        empty_ledger = []
        updated_ledger = enrique_payment(empty_ledger)
        
        # Should have entries from Jan 2025 to current date
        enrique_entries = [row for row in updated_ledger if "Enrique" in row.description]
        
        # Verify at least one entry exists (depending on current date)
        assert len(enrique_entries) >= 1
        
        # Check first entry details
        first_entry = enrique_entries[0]
        assert first_entry.amount == Decimal('-105.59')
        assert first_entry.category == 'payment'
        assert first_entry.re == Decimal('-105.59')  # Assigned to RE family
        assert first_entry.jj == Decimal('0')
        assert first_entry.ks == Decimal('0')
        assert first_entry.dj == Decimal('0')
    
    def test_daniel_payment_empty_ledger(self):
        """Test Daniel payment generation with empty ledger"""
        empty_ledger = []
        updated_ledger = daniel_payment(empty_ledger)
        
        daniel_entries = [row for row in updated_ledger if "Daniel" in row.description]
        
        assert len(daniel_entries) >= 1
        
        first_entry = daniel_entries[0]
        assert first_entry.amount == Decimal('-69.73')
        assert first_entry.category == 'payment'
        assert first_entry.dj == Decimal('-69.73')  # Assigned to DJ family
        assert first_entry.jj == Decimal('0')
        assert first_entry.ks == Decimal('0')
        assert first_entry.re == Decimal('0')
    
    def test_seth_payment_empty_ledger(self):
        """Test Seth payment generation with empty ledger"""
        empty_ledger = []
        updated_ledger = seth_payment(empty_ledger)
        
        seth_entries = [row for row in updated_ledger if "Seth" in row.description]
        
        assert len(seth_entries) >= 1
        
        first_entry = seth_entries[0]
        assert first_entry.amount == Decimal('-77.00')
        assert first_entry.category == 'payment'
        assert first_entry.ks == Decimal('-77.00')  # Assigned to KS family
        assert first_entry.jj == Decimal('0')
        assert first_entry.dj == Decimal('0')
        assert first_entry.re == Decimal('0')
    
    def test_wsj_charge_empty_ledger(self):
        """Test WSJ charge generation with empty ledger"""
        empty_ledger = []
        updated_ledger = wsj_charge(empty_ledger)
        
        wsj_entries = [row for row in updated_ledger if "WSJ" in row.description]
        
        assert len(wsj_entries) >= 1
        
        first_entry = wsj_entries[0]
        assert first_entry.amount == Decimal('70.76')
        assert first_entry.category == 'misc'
        # WSJ is split: JJ=1 share, DJ=2 shares, so JJ gets 1/3, DJ gets 2/3
        assert first_entry.jj == Decimal('23.59')  # 70.76 * 1/3 rounded
        assert first_entry.dj == Decimal('47.17')  # 70.76 * 2/3 rounded
        assert first_entry.ks == Decimal('0')
        assert first_entry.re == Decimal('0')
    
    def test_wsj_charge_4_week_schedule(self):
        """Test that WSJ charges are scheduled every 4 weeks"""
        empty_ledger = []
        updated_ledger = wsj_charge(empty_ledger)
        
        wsj_entries = [row for row in updated_ledger if "WSJ" in row.description]
        wsj_dates = [row.date for row in wsj_entries]
        wsj_dates.sort()
        
        # Check that consecutive dates are 28 days apart (4 weeks)
        for i in range(1, len(wsj_dates)):
            days_diff = (wsj_dates[i] - wsj_dates[i-1]).days
            assert days_diff == 28, f"WSJ dates should be 28 days apart, got {days_diff}"
    
    def test_duplicate_prevention(self):
        """Test that existing entries prevent duplicates"""
        # Create a ledger with an existing Enrique payment
        existing_payment = LedgerRow(
            description="Enrique Gonzalez",
            date=date(2025, 1, 6),
            amount=Decimal('-105.59'),
            category='payment',
            shares_jj=None, shares_ks=None, shares_dj=None, shares_re=1,
            shares_total=1,
            jj=Decimal('0'), ks=Decimal('0'), dj=Decimal('0'), re=Decimal('-105.59')
        )
        
        ledger_with_existing = [existing_payment]
        updated_ledger = enrique_payment(ledger_with_existing)
        
        # Should not duplicate the existing entry
        enrique_entries = [row for row in updated_ledger if "Enrique" in row.description]
        
        # Count entries for Jan 6, 2025 - should be exactly 1
        jan_6_entries = [row for row in enrique_entries if row.date == date(2025, 1, 6)]
        assert len(jan_6_entries) == 1, "Should not duplicate existing entry"
    
    def test_get_existing_entries(self):
        """Test the helper function that finds existing entries"""
        test_ledger = [
            LedgerRow(
                description="Enrique Gonzalez",
                date=date(2025, 1, 6),
                amount=Decimal('-105.59'),
                category='payment',
                shares_jj=None, shares_ks=None, shares_dj=None, shares_re=1,
                shares_total=1,
                jj=Decimal('0'), ks=Decimal('0'), dj=Decimal('0'), re=Decimal('-105.59')
            ),
            LedgerRow(
                description="Daniel Eaton",
                date=date(2025, 1, 3),
                amount=Decimal('-69.73'),
                category='payment',
                shares_jj=None, shares_ks=None, shares_dj=1, shares_re=None,
                shares_total=1,
                jj=Decimal('0'), ks=Decimal('0'), dj=Decimal('-69.73'), re=Decimal('0')
            )
        ]
        
        enrique_dates = _get_existing_entries(test_ledger, "Enrique")
        daniel_dates = _get_existing_entries(test_ledger, "Daniel")
        
        assert date(2025, 1, 6) in enrique_dates
        assert date(2025, 1, 3) in daniel_dates
        assert len(enrique_dates) == 1
        assert len(daniel_dates) == 1
    
    def test_update_all_scheduled(self):
        """Test the comprehensive update function"""
        empty_ledger = []
        updated_ledger = update_all_scheduled(empty_ledger)
        
        # Should have entries from all scheduled payment types
        enrique_entries = [row for row in updated_ledger if "Enrique" in row.description]
        daniel_entries = [row for row in updated_ledger if "Daniel" in row.description]
        seth_entries = [row for row in updated_ledger if "Seth" in row.description]
        wsj_entries = [row for row in updated_ledger if "WSJ" in row.description]
        
        assert len(enrique_entries) >= 1
        assert len(daniel_entries) >= 1
        assert len(seth_entries) >= 1
        assert len(wsj_entries) >= 1
        
        # Verify no duplicates were created
        all_entries = updated_ledger
        descriptions_and_dates = [(row.description, row.date) for row in all_entries]
        unique_entries = set(descriptions_and_dates)
        
        assert len(descriptions_and_dates) == len(unique_entries), "Should not create duplicate entries"