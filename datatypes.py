from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Dict, Optional
from datetime import date

Money = Decimal       # keep full-precision cents

@dataclass
class Device:
    number: str                  # E.164 or digits only
    kind: str                    # "voice" | "wearable" | "connected"
    family: str                  # "JJ" / "KS" / "DJ" / "RE"
    adults: int = 2              # default; used for Netflix split

@dataclass
class BillTotals:
    cycle_start: date
    cycle_end: date
    due_date: date
    total_due: Money
    voice_subtotal: Money
    wearable_subtotal: Money
    connected_subtotal: Money
    netflix_charge: Money
    equipments: Dict[str, Money]        # number → net installment
    usage: Dict[str, Money]             # number → one-off usage

@dataclass
class LedgerRow:
    description: str            # "8 voice lines"
    date: date                  # Due date 
    amount: Money               # Total amount
    category: str               # "service", "equipment", "payment", "misc"
    date_posted: Optional[date] = None  # Posted date (can be blank)
    shares_jj: Optional[int] = None     # Share units for JJ
    shares_ks: Optional[int] = None     # Share units for KS  
    shares_dj: Optional[int] = None     # Share units for DJ
    shares_re: Optional[int] = None     # Share units for RE
    shares_total: Optional[int] = None  # Total share units
    jj: Money = Money(0)        # Cost for JJ
    ks: Money = Money(0)        # Cost for KS
    dj: Money = Money(0)        # Cost for DJ
    re: Money = Money(0)        # Cost for RE