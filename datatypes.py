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
    description: str            # “Feb 2025 Voice Plan”
    date: date
    jj: Money = Money(0)
    ks: Money = Money(0)
    dj: Money = Money(0)
    re: Money = Money(0)