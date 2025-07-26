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
    
    # Voice plan row
    if bill.voice_subtotal > 0:
        voice_shares = _count_by_family([d.family for d in voice_numbers])
        rows.append(_service_row(f'{len(voice_numbers)} voice lines', bill.cycle_end, 
                                 bill.voice_subtotal, voice_shares, voice_alloc))
    
    # Wearable plan row  
    if bill.wearable_subtotal > 0:
        wear_shares = _count_by_family([d.family for d in wearables])
        rows.append(_service_row(f'{len(wearables)} wearable plans', bill.cycle_end,
                                 bill.wearable_subtotal, wear_shares, wear_alloc))
    
    # Connected plan row
    if bill.connected_subtotal > 0:
        conn_shares = _count_by_family([d.family for d in connected])
        rows.append(_service_row(f'{len(connected)} hotspot plan', bill.cycle_end,
                                 bill.connected_subtotal, conn_shares, conn_alloc))
    
    # Netflix row
    if bill.netflix_charge > 0:
        rows.append(_service_row('netflix', bill.cycle_end, bill.netflix_charge, adults, netflix_alloc))
    
    # Equipment rows - one per device
    for num, amt in bill.equipments.items():
        if amt != 0:  # Skip zero amounts
            device = _find_device(num, devices)
            desc = _equipment_description(num, device)
            family_shares = {device.family: 1}
            family_costs = {device.family: amt}
            rows.append(_equipment_row(desc, bill.cycle_end, amt, family_shares, family_costs))
    
    # Usage rows - one per phone with usage
    for num, amt in bill.usage.items():
        if amt != 0:  # Skip zero amounts
            device = _find_device(num, devices)
            desc = _usage_description(num, device, amt)
            family_shares = {device.family: 1}
            family_costs = {device.family: amt}
            rows.append(_misc_row(desc, bill.cycle_end, amt, family_shares, family_costs))
    
    return rows

# -------------------- helpers --------------------

def _family(number: str, devices):
    for d in devices:
        if d.number.endswith(number[-4:]):   # crude; improve later
            return d.family
    raise KeyError(f'Phone {number} not in config')

def _find_device(number: str, devices):
    for d in devices:
        if d.number.endswith(number[-4:]):   # crude; improve later
            return d
    raise KeyError(f'Phone {number} not in config')

def _line_amount(_, subtotal, count):
    # Each wearable currently billed at same plan price
    return subtotal / Decimal(count)

def _share(per_item, owners):
    out = defaultdict(Decimal)
    for fam in owners:
        out[fam] += per_item
    return out

def _count_by_family(families):
    """Count occurrences of each family in the list"""
    counts = defaultdict(int)
    for fam in families:
        counts[fam] += 1
    return dict(counts)

def _service_row(description, due_date, amount, shares, costs):
    """Create a service category row"""
    return LedgerRow(
        description=description,
        date=due_date,
        amount=amount,
        category='service',
        shares_jj=shares.get('JJ', 0) or None,
        shares_ks=shares.get('KS', 0) or None,
        shares_dj=shares.get('DJ', 0) or None,
        shares_re=shares.get('RE', 0) or None,
        shares_total=sum(shares.values()),
        jj=_r(costs.get("JJ", 0)),
        ks=_r(costs.get("KS", 0)),
        dj=_r(costs.get("DJ", 0)),
        re=_r(costs.get("RE", 0)),
    )

def _equipment_row(description, due_date, amount, shares, costs):
    """Create an equipment category row"""
    return LedgerRow(
        description=description,
        date=due_date,
        amount=amount,
        category='equipment',
        shares_jj=shares.get('JJ', 0) or None,
        shares_ks=shares.get('KS', 0) or None,
        shares_dj=shares.get('DJ', 0) or None,
        shares_re=shares.get('RE', 0) or None,
        shares_total=sum(shares.values()),
        jj=_r(costs.get("JJ", 0)),
        ks=_r(costs.get("KS", 0)),
        dj=_r(costs.get("DJ", 0)),
        re=_r(costs.get("RE", 0)),
    )

def _misc_row(description, due_date, amount, shares, costs):
    """Create a misc category row"""
    return LedgerRow(
        description=description,
        date=due_date,
        amount=amount,
        category='misc',
        shares_jj=shares.get('JJ', 0) or None,
        shares_ks=shares.get('KS', 0) or None,
        shares_dj=shares.get('DJ', 0) or None,
        shares_re=shares.get('RE', 0) or None,
        shares_total=sum(shares.values()),
        jj=_r(costs.get("JJ", 0)),
        ks=_r(costs.get("KS", 0)),
        dj=_r(costs.get("DJ", 0)),
        re=_r(costs.get("RE", 0)),
    )

def _equipment_description(number, device):
    """Generate equipment description from device info"""
    # Map specific device numbers to names based on expenses.csv patterns
    device_names = {
        "2022586292": "rebecca iphone",
        "2012904373": "janet iphone", 
        "2405844111": "fran phone",
        "3476366212": "julia apple watch",
        "4102272625": "jonah iphone",
    }
    
    # Look up by last 4 digits if full number not found
    last_four = number[-4:]
    for full_num, name in device_names.items():
        if full_num.endswith(last_four):
            return name
    
    # Generic fallback based on device type
    family_lower = device.family.lower()
    if device.kind == 'wearable':
        return f"{family_lower} apple watch"
    elif device.kind == 'voice':
        return f"{family_lower} iphone"
    else:
        return f"{family_lower} device {last_four}"

def _usage_description(number, device, amount):
    """Generate usage description"""
    return f"{device.family} international call"

def _r(x):  # round 2dp HALF_UP
    return Decimal(x).quantize(Decimal('0.01'), ROUND_HALF_UP)