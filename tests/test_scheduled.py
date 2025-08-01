"""
Tests for scheduled payment and expense functions.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from family_mobile_ledger.scheduled import (
    enrique_payment, daniel_payment, seth_payment, wsj_charge,
    update_all_scheduled, _get_existing_entries,
    jonah_payment_for_bill, add_jonah_payment_if_missing
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


class TestJonahPayments:
    """Test Jonah payment calculation and integration"""
    
    def test_jonah_payment_calculation(self):
        """Test Jonah payment calculation from T-Mobile bill"""
        due_date = date(2025, 6, 24)
        
        # Sample T-Mobile bill entries
        bill_rows = [
            LedgerRow(
                description="voice lines",
                date=due_date,
                amount=Decimal('100.00'),
                category='service',
                shares_jj=1, shares_ks=1, shares_dj=1, shares_re=1,
                shares_total=4,
                jj=Decimal('25.00'),
                ks=Decimal('25.00'),
                dj=Decimal('25.00'),
                re=Decimal('25.00')
            ),
            LedgerRow(
                description="jonah iphone",
                date=due_date,
                amount=Decimal('33.34'),
                category='equipment',
                shares_jj=1, shares_ks=None, shares_dj=None, shares_re=None,
                shares_total=1,
                jj=Decimal('33.34'),
                ks=Decimal('0.00'),
                dj=Decimal('0.00'),
                re=Decimal('0.00')
            )
        ]
        
        jonah_payment = jonah_payment_for_bill(bill_rows, due_date)
        
        assert jonah_payment is not None
        assert jonah_payment.amount == Decimal('-58.34')  # -(25.00 + 33.34)
        assert jonah_payment.description == "Jonah"
        assert jonah_payment.date == due_date
        assert jonah_payment.category == "payment"
        assert jonah_payment.jj == Decimal('-58.34')
    
    def test_jonah_payment_no_jj_costs(self):
        """Test that no payment is created when bill has no JJ costs"""
        due_date = date(2025, 6, 24)
        
        bill_rows = [
            LedgerRow(
                description="rebecca iphone",
                date=due_date,
                amount=Decimal('26.25'),
                category='equipment',
                shares_jj=None, shares_ks=None, shares_dj=None, shares_re=1,
                shares_total=1,
                jj=Decimal('0.00'),
                ks=Decimal('0.00'),
                dj=Decimal('0.00'),
                re=Decimal('26.25')
            )
        ]
        
        jonah_payment = jonah_payment_for_bill(bill_rows, due_date)
        
        assert jonah_payment is None
    
    def test_add_jonah_payment_if_missing(self):
        """Test adding Jonah payment to existing ledger"""
        due_date = date(2025, 6, 24)
        
        # Existing ledger without Jonah payment
        existing_ledger = [
            LedgerRow(
                description="voice lines",
                date=due_date,
                amount=Decimal('100.00'),
                category='service',
                shares_jj=1, shares_ks=1, shares_dj=1, shares_re=1,
                shares_total=4,
                jj=Decimal('25.00'),
                ks=Decimal('25.00'),
                dj=Decimal('25.00'),
                re=Decimal('25.00')
            )
        ]
        
        # Bill rows that were just added
        bill_rows = existing_ledger
        
        updated_ledger = add_jonah_payment_if_missing(existing_ledger, bill_rows, due_date)
        
        # Should have added Jonah payment
        assert len(updated_ledger) == 2
        
        jonah_payments = [row for row in updated_ledger 
                         if "jonah" in row.description.lower() and row.category == "payment"]
        assert len(jonah_payments) == 1
        assert jonah_payments[0].amount == Decimal('-25.00')
    
    def test_jonah_payment_duplicate_prevention(self):
        """Test that duplicate Jonah payments are not created"""
        due_date = date(2025, 6, 24)
        
        # Existing ledger with Jonah payment already
        existing_ledger = [
            LedgerRow(
                description="voice lines",
                date=due_date,
                amount=Decimal('100.00'),
                category='service',
                shares_jj=1, shares_ks=1, shares_dj=1, shares_re=1,
                shares_total=4,
                jj=Decimal('25.00'),
                ks=Decimal('25.00'),
                dj=Decimal('25.00'),
                re=Decimal('25.00')
            ),
            LedgerRow(
                description="Jonah",
                date=due_date,
                amount=Decimal('-25.00'),
                category='payment',
                shares_jj=1, shares_ks=None, shares_dj=None, shares_re=None,
                shares_total=1,
                jj=Decimal('-25.00'),
                ks=Decimal('0.00'),
                dj=Decimal('0.00'),
                re=Decimal('0.00')
            )
        ]
        
        # Try to add Jonah payment again
        bill_rows = [existing_ledger[0]]  # Just the bill entry
        updated_ledger = add_jonah_payment_if_missing(existing_ledger, bill_rows, due_date)
        
        # Should not have added another Jonah payment
        assert len(updated_ledger) == 2
        
        jonah_payments = [row for row in updated_ledger 
                         if "jonah" in row.description.lower() and row.category == "payment"]
        assert len(jonah_payments) == 1  # Still only one


class TestWSJJonahIntegration:
    """Test WSJ charges automatically include Jonah payments"""
    
    def test_wsj_includes_jonah_payment(self):
        """Test that WSJ charges automatically create Jonah payments"""
        empty_ledger = []
        updated_ledger = wsj_charge(empty_ledger)
        
        # Separate WSJ charges from Jonah payments
        wsj_charges = [row for row in updated_ledger if "WSJ" in row.description and row.category == "misc"]
        jonah_payments = [row for row in updated_ledger if "jonah" in row.description.lower() and row.category == "payment"]
        
        # Should have equal numbers
        assert len(wsj_charges) > 0, "Should have WSJ charges"
        assert len(jonah_payments) > 0, "Should have Jonah payments"
        assert len(wsj_charges) == len(jonah_payments), "Should have equal WSJ charges and Jonah payments"
        
        # Verify dates match
        wsj_dates = {row.date for row in wsj_charges}
        jonah_dates = {row.date for row in jonah_payments}
        assert wsj_dates == jonah_dates, "WSJ and Jonah payment dates should match"
    
    def test_wsj_jonah_amounts(self):
        """Test that WSJ Jonah payment amounts are correct"""
        empty_ledger = []
        updated_ledger = wsj_charge(empty_ledger)
        
        wsj_charges = [row for row in updated_ledger if "WSJ" in row.description and row.category == "misc"]
        jonah_payments = [row for row in updated_ledger if "jonah" in row.description.lower() and row.category == "payment"]
        
        for wsj_charge_row in wsj_charges:
            # Find corresponding Jonah payment
            jonah_payment_row = next(
                (row for row in jonah_payments if row.date == wsj_charge_row.date),
                None
            )
            
            assert jonah_payment_row is not None, f"Missing Jonah payment for WSJ charge on {wsj_charge_row.date}"
            
            # Verify amounts
            assert wsj_charge_row.amount == Decimal('70.76'), "WSJ charge should be $70.76"
            assert wsj_charge_row.jj == Decimal('23.59'), "WSJ JJ portion should be $23.59"
            assert jonah_payment_row.amount == Decimal('-23.59'), "Jonah payment should be -$23.59"
            assert jonah_payment_row.jj == Decimal('-23.59'), "Jonah payment JJ cost should be -$23.59"
    
    def test_wsj_partial_duplicate_handling(self):
        """Test adding missing Jonah payment when WSJ charge already exists"""
        # Create ledger with WSJ charge but no Jonah payment
        existing_date = date(2024, 9, 15)
        existing_ledger = [
            LedgerRow(
                description="WSJ",
                date=existing_date,
                amount=Decimal('70.76'),
                category='misc',
                shares_jj=1, shares_ks=0, shares_dj=2, shares_re=0,
                shares_total=3,
                jj=Decimal('23.59'),
                ks=Decimal('0.00'),
                dj=Decimal('47.17'),
                re=Decimal('0.00')
            )
        ]
        
        updated_ledger = wsj_charge(existing_ledger)
        
        # Should have added the missing Jonah payment
        jonah_payments = [row for row in updated_ledger 
                         if row.date == existing_date and "jonah" in row.description.lower() 
                         and row.category == "payment"]
        
        assert len(jonah_payments) == 1, "Should have added missing Jonah payment"
        assert jonah_payments[0].amount == Decimal('-23.59'), "Jonah payment amount should be correct"