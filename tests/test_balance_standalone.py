#!/usr/bin/env python3
"""
Standalone test for balance reporting functionality.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from datetime import date
from decimal import Decimal
from typing import Dict, List
from family_mobile_ledger.datatypes import LedgerRow

def calculate_family_balances(ledger: List[LedgerRow]) -> Dict[str, Decimal]:
    """
    Calculate outstanding balance for each family.
    
    Positive balance = family owes money (charges > payments)
    Negative balance = family has credit (payments > charges)
    
    Returns:
        Dict mapping family codes to their outstanding balances
    """
    family_balances = {
        'JJ': Decimal('0'),
        'KS': Decimal('0'), 
        'DJ': Decimal('0'),
        'RE': Decimal('0')
    }
    
    for row in ledger:
        # Add family costs (positive = they owe)
        family_balances['JJ'] += row.jj
        family_balances['KS'] += row.ks
        family_balances['DJ'] += row.dj
        family_balances['RE'] += row.re
    
    return family_balances

def format_balance_report(balances: Dict[str, Decimal]) -> str:
    """
    Format family balances in an email-friendly format.
    """
    family_names = {
        'JJ': 'Jonah & Janet',
        'KS': 'Kelly & Seth', 
        'DJ': 'Daniel & Jaime',
        'RE': 'Ricardo & Enrique'
    }
    
    report_lines = []
    report_lines.append("=== FAMILY MOBILE LEDGER BALANCES ===")
    report_lines.append("")
    
    total_outstanding = Decimal('0')
    
    for family_code, balance in balances.items():
        family_name = family_names[family_code]
        
        if balance > 0:
            status = f"owes ${balance:.2f}"
            total_outstanding += balance
        elif balance < 0:
            status = f"has credit of ${abs(balance):.2f}"
        else:
            status = "balanced (${:.2f})".format(balance)
        
        report_lines.append(f"{family_name} ({family_code}): {status}")
    
    report_lines.append("")
    report_lines.append(f"Total Outstanding: ${total_outstanding:.2f}")
    report_lines.append("")
    report_lines.append("(Generated automatically by Family Mobile Ledger)")
    
    return "\n".join(report_lines)

def test_balance_calculation():
    """Test balance calculation with sample ledger entries"""
    print("🧪 Testing balance calculation...")
    
    # Create sample ledger entries
    sample_ledger = [
        # T-Mobile bill charges
        LedgerRow(
            description="Voice lines - Jan 2025",
            date=date(2025, 1, 15),
            amount=Decimal('200.00'),
            category='service',
            jj=Decimal('50.00'),
            ks=Decimal('75.00'),
            dj=Decimal('40.00'),
            re=Decimal('35.00')
        ),
        # Payment from Enrique 
        LedgerRow(
            description="Enrique Gonzalez",
            date=date(2025, 1, 6),
            amount=Decimal('-105.59'),
            category='payment',
            re=Decimal('-105.59')
        ),
        # Payment from Daniel
        LedgerRow(
            description="Daniel Eaton", 
            date=date(2025, 1, 3),
            amount=Decimal('-69.73'),
            category='payment',
            dj=Decimal('-69.73')
        ),
        # WSJ charge
        LedgerRow(
            description="WSJ",
            date=date(2025, 1, 10),
            amount=Decimal('70.76'),
            category='misc',
            jj=Decimal('23.59'),
            dj=Decimal('47.17')
        ),
        # Jonah payment for WSJ
        LedgerRow(
            description="Jonah",
            date=date(2025, 1, 10),
            amount=Decimal('-23.59'),
            category='payment',
            jj=Decimal('-23.59')
        )
    ]
    
    # Calculate balances
    balances = calculate_family_balances(sample_ledger)
    
    print("✅ Calculated balances:")
    for family, balance in balances.items():
        print(f"   {family}: ${balance:.2f}")
    
    # Expected balances:
    # JJ: 50.00 + 23.59 - 23.59 = 50.00 (owes $50.00)
    # KS: 75.00 (owes $75.00)  
    # DJ: 40.00 + 47.17 - 69.73 = 17.44 (owes $17.44)
    # RE: 35.00 - 105.59 = -70.59 (has credit of $70.59)
    
    expected_balances = {
        'JJ': Decimal('50.00'),
        'KS': Decimal('75.00'),
        'DJ': Decimal('17.44'),
        'RE': Decimal('-70.59')
    }
    
    for family, expected in expected_balances.items():
        actual = balances[family]
        assert actual == expected, f"{family} balance should be ${expected}, got ${actual}"
    
    print("✅ All balance calculations are correct")
    return True

def test_balance_formatting():
    """Test the email-friendly balance report formatting"""
    print("\n🧪 Testing balance report formatting...")
    
    sample_balances = {
        'JJ': Decimal('50.00'),
        'KS': Decimal('75.00'), 
        'DJ': Decimal('17.44'),
        'RE': Decimal('-70.59')
    }
    
    report = format_balance_report(sample_balances)
    print("✅ Generated balance report:")
    print("\n" + "="*50)
    print(report)
    print("="*50)
    
    # Verify report contains expected elements
    assert "FAMILY MOBILE LEDGER BALANCES" in report
    assert "Jonah & Janet (JJ): owes $50.00" in report
    assert "Kelly & Seth (KS): owes $75.00" in report
    assert "Daniel & Jaime (DJ): owes $17.44" in report
    assert "Ricardo & Enrique (RE): has credit of $70.59" in report
    assert "Total Outstanding: $142.44" in report
    assert "Generated automatically by Family Mobile Ledger" in report
    
    print("✅ Report format is correct and email-ready")
    return True

def test_zero_balances():
    """Test formatting when balances are zero"""
    print("\n🧪 Testing zero balance formatting...")
    
    zero_balances = {
        'JJ': Decimal('0.00'),
        'KS': Decimal('0.00'),
        'DJ': Decimal('0.00'), 
        'RE': Decimal('0.00')
    }
    
    report = format_balance_report(zero_balances)
    print("✅ Zero balance report:")
    print("\n" + "-"*30)
    print(report)
    print("-"*30)
    
    # Should show "balanced" for zero amounts
    assert "balanced ($0.00)" in report
    assert "Total Outstanding: $0.00" in report
    
    print("✅ Zero balance formatting works correctly")
    return True

if __name__ == '__main__':
    try:
        test1 = test_balance_calculation()
        test2 = test_balance_formatting()
        test3 = test_zero_balances()
        
        if all([test1, test2, test3]):
            print("\n🏆 All balance reporting tests passed!")
            print("🎉 Balance reporting is working perfectly!")
            print("📋 Features:")
            print("   ✅ Accurate balance calculation")
            print("   ✅ Email-friendly formatting")
            print("   ✅ Clear family names and amounts")
            print("   ✅ Outstanding total calculation")
            print("   ✅ Credit vs debt indication")
        else:
            print("\n💥 Some tests failed!")
            exit(1)
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)