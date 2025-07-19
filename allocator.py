from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from .datatypes import BillTotals, LedgerRow
from .config import load_devices, adults_by_family

def allocate(bill: BillTotals) -> list[LedgerRow]:
    devices = load_devices()
    voice_numbers = [d for d in devices if d.kind == 'voice']
    wearables     = [d for d in devices if d.kind == 'wearable']
    connected     = [d for d in devices if d.kind == 'connected']
    adults        = adults_by_family(devices)

    # Rule A – voice
    per_line = bill.voice_subtotal / Decimal(len(voice_numbers))
    voice_alloc = _share(per_line, [d.family for d in voice_numbers])

    # Rule B – wearables pass-through
    wear_alloc = defaultdict(Decimal)
    for d in wearables:
        wear_alloc[d.family] += _line_amount(d.number, bill.wearable_subtotal, len(wearables))

    # Rule C – connected pass-through (only one line today)
    conn_alloc = defaultdict(Decimal)
    for d in connected:
        conn_alloc[d.family] += bill.connected_subtotal

    # Rule D – equipment
    equip_alloc = defaultdict(Decimal)
    for num, amt in bill.equipments.items():
        fam = _family(num, devices)
        equip_alloc[fam] += amt

    # Rule E – Netflix split by adults
    netflix_alloc = defaultdict(Decimal)
    total_adults = sum(adults.values())
    for fam, n in adults.items():
        netflix_alloc[fam] = bill.netflix_charge * Decimal(n) / Decimal(total_adults)

    # Rule F – usage
    usage_alloc = defaultdict(Decimal)
    for num, amt in bill.usage.items():
        fam = _family(num, devices)
        usage_alloc[fam] += amt

    # Stitch to LedgerRow list, rounding at write-time
    rows = []
    rows += _rows('Voice Plan', bill.cycle_end, voice_alloc)
    rows += _rows('Wearable Plan', bill.cycle_end, wear_alloc)
    rows += _rows('Connected Plan', bill.cycle_end, conn_alloc)
    rows += _rows('Equipment', bill.cycle_end, equip_alloc)
    rows += _rows('Netflix', bill.cycle_end, netflix_alloc)
    rows += _rows('Usage', bill.cycle_end, usage_alloc)
    return rows

# -------------------- helpers --------------------

def _family(number: str, devices):
    for d in devices:
        if d.number.endswith(number[-4:]):   # crude; improve later
            return d.family
    raise KeyError(f'Phone {number} not in config')

def _line_amount(_, subtotal, count):
    # Each wearable currently billed at same plan price
    return subtotal / Decimal(count)

def _share(per_item, owners):
    out = defaultdict(Decimal)
    for fam in owners:
        out[fam] += per_item
    return out

def _rows(label, asof, bucket):
    return [LedgerRow(
            description=f'{label} {asof:%b %Y}',
            date=asof,
            jj=_r(bucket.get("JJ", 0)),
            ks=_r(bucket.get("KS", 0)),
            dj=_r(bucket.get("DJ", 0)),
            re=_r(bucket.get("RE", 0)),
        ) for _ in (0,)]  # one row

def _r(x):  # round 2dp HALF_UP
    return Decimal(x).quantize(Decimal('0.01'), ROUND_HALF_UP)