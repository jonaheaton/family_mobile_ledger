"""
Allocator rule tests for the **October 2024** bill.

We construct a `BillTotals` object that reflects the ledger rows for
October 2024 and monkey‑patch:
  • `family_mobile_ledger.allocator.load_devices` to reflect the **7 active voice lines** in Oct 2024
  • `family_mobile_ledger.allocator.adults_by_family` to emulate the **Netflix share rule used then**

We then assert that the allocator reproduces the per‑family amounts found in
`expenses.csv` for that month (ignoring `misc` and `payment` rows).
"""
from decimal import Decimal
from datetime import date
from typing import Dict, List

import pytest

from family_mobile_ledger import allocator
from family_mobile_ledger.datatypes import BillTotals, Device, LedgerRow


# -----------------------------
# Constants from expenses.csv
# -----------------------------
VOICE_SUBTOTAL = Decimal("200.00")
WEARABLE_SUBTOTAL = Decimal("29.00")
CONNECTED_SUBTOTAL = Decimal("0.00")
NETFLIX = Decimal("8.50")

# Equipment rows (device number → amount) per CSV for Oct 2024
EQUIPMENT: Dict[str, Decimal] = {
    "2022586292": Decimal("26.25"),  # Rebecca iPhone → RE
    "2012904373": Decimal("25.00"),  # Janet iPhone   → JJ
    "2405844111": Decimal("10.75"),  # "Fran phone"   → KS
    "3476366212": Decimal("8.34"),   # Julia watch    → RE
    "4102272625": Decimal("33.34"),  # Jonah iPhone   → JJ
}

USAGE: Dict[str, Decimal] = {}

# Expected per‑category allocations (rounded, as written to the ledger)
EXPECTED_VOICE = {"JJ": Decimal("57.14"), "KS": Decimal("57.14"), "DJ": Decimal("28.57"), "RE": Decimal("57.14")}
# rules for allocating wearables changed in 2025
EXPECTED_WEAR  = {"JJ": Decimal("0.00"),  "KS": Decimal("14.50"), "DJ": Decimal("0.00"),  "RE": Decimal("14.50")}
EXPECTED_NETFLIX = {"JJ": Decimal("2.43"), "KS": Decimal("2.43"), "DJ": Decimal("1.21"), "RE": Decimal("2.43")}
EXPECTED_EQUIP = {"JJ": Decimal("58.34"), "KS": Decimal("10.75"), "DJ": Decimal("0.00"),  "RE": Decimal("34.59")}
EXPECTED_CONN  = {"JJ": Decimal("0.00"),  "KS": Decimal("0.00"),  "DJ": Decimal("0.00"),  "RE": Decimal("0.00")}
EXPECTED_USAGE = {"JJ": Decimal("0.00"),  "KS": Decimal("0.00"),  "DJ": Decimal("0.00"),  "RE": Decimal("0.00")}


def _devices_oct_2024() -> List[Device]:
    """Active devices for Oct 2024: 7 voice, 2 wearables, 0 connected.

    Voice counts match the CSV Netflix share weights (2,2,1,2) and the
    $200 voice subtotal split into 7 equal shares.
    """
    return [
        # JJ – 2 voice
        Device(number="4102272625", kind="voice", family="JJ", adults=2),
        Device(number="2012904373", kind="voice", family="JJ", adults=2),
        # KS – 2 voice (+ wearable)
        Device(number="2405844111", kind="voice", family="KS", adults=2),
        Device(number="4433266326", kind="voice", family="KS", adults=2),
        Device(number="8575767313", kind="wearable", family="KS", adults=2),
        # DJ – 1 voice
        Device(number="3014528244", kind="voice", family="DJ", adults=1),
        # RE – 2 voice (+ wearable)
        Device(number="2022586292", kind="voice", family="RE", adults=2),
        Device(number="9179125315", kind="voice", family="RE", adults=2),
        Device(number="3476366212", kind="wearable", family="RE", adults=2),
    ]


@pytest.fixture()
def patched_devices_and_adults(monkeypatch):
    devices = _devices_oct_2024()

    # Patch load_devices to return exactly the Oct 2024 active set
    monkeypatch.setattr(allocator, "load_devices", lambda: devices)

    # Netflix in Oct 2024 was split in proportion to **voice line counts**:
    # JJ=2, KS=2, DJ=1, RE=2  → shares total = 7
    shares = {"JJ": 2, "KS": 2, "DJ": 1, "RE": 2}
    monkeypatch.setattr(allocator, "adults_by_family", lambda _devices: shares)

    return devices


@pytest.fixture()
def oct_bill() -> BillTotals:
    return BillTotals(
        cycle_start=date(2024, 9, 4),  # not used in allocator assertions
        cycle_end=date(2024, 10, 24),
        due_date=date(2024, 10, 24),
        total_due=Decimal("0.00"),  # allocator doesn’t use total_due
        voice_subtotal=VOICE_SUBTOTAL,
        wearable_subtotal=WEARABLE_SUBTOTAL,
        connected_subtotal=CONNECTED_SUBTOTAL,
        netflix_charge=NETFLIX,
        equipments=EQUIPMENT,
        usage=USAGE,
    )


# -----------------------------
# Tests
# -----------------------------

def _row_dict(row: LedgerRow) -> Dict[str, Decimal]:
    return {"JJ": row.jj, "KS": row.ks, "DJ": row.dj, "RE": row.re}


def _get(rows, label):
    desc = f"{label} {date(2024, 10, 24):%b %Y}"
    for r in rows:
        if r.description == desc:
            return r
    raise AssertionError(f"Row not found: {desc}\nHave: {[r.description for r in rows]}")


def test_voice_allocation_oct(patched_devices_and_adults, oct_bill):
    rows = allocator.allocate(oct_bill)
    voice = _get(rows, "Voice Plan")
    assert _row_dict(voice) == EXPECTED_VOICE


def test_wearable_allocation_oct(patched_devices_and_adults, oct_bill):
    rows = allocator.allocate(oct_bill)
    wear = _get(rows, "Wearable Plan")
    assert _row_dict(wear) == EXPECTED_WEAR


def test_connected_allocation_oct(patched_devices_and_adults, oct_bill):
    rows = allocator.allocate(oct_bill)
    conn = _get(rows, "Connected Plan")
    assert _row_dict(conn) == EXPECTED_CONN


def test_equipment_allocation_oct(patched_devices_and_adults, oct_bill):
    rows = allocator.allocate(oct_bill)
    equip = _get(rows, "Equipment")
    assert _row_dict(equip) == EXPECTED_EQUIP


def test_netflix_allocation_oct(patched_devices_and_adults, oct_bill):
    rows = allocator.allocate(oct_bill)
    nflx = _get(rows, "Netflix")
    assert _row_dict(nflx) == EXPECTED_NETFLIX


def test_usage_allocation_oct(patched_devices_and_adults, oct_bill):
    rows = allocator.allocate(oct_bill)
    usage = _get(rows, "Usage")
    assert _row_dict(usage) == EXPECTED_USAGE