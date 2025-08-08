# %%
import pdfplumber, re
from decimal import Decimal
from pathlib import Path
from .datatypes import BillTotals
from datetime import datetime, date

_MONEY = re.compile(r'\$?(-?\d+\.\d{2})')

def _to_money(s: str) -> Decimal:
    return Decimal(_MONEY.search(s).group(1))

def _detect_non_allocatable_voice_lines(text: str) -> list[dict]:
    """
    Detect voice lines that shouldn't be allocated (e.g., old numbers during transfers).
    
    Looks for voice lines in the bill summary that have:
    - Line type "Voice" 
    - Empty/null Plans column (indicated by "-" or blank)
    - Descriptors like "Old number", "Transferred", etc.
    
    Returns list of dicts with 'number' and 'reason' keys.
    """
    non_allocatable = []
    
    # Look for bill summary section lines that match this pattern:
    # (xxx) xxx-xxxx - Description Voice Plans Equipment Services $x.xx
    # We want to find Voice lines where Plans column is "-" (empty/null)
    
    # Split text into lines and look for the summary section
    lines = text.split('\n')
    in_summary_section = False
    
    for line in lines:
        # Start processing when we find "THIS BILL SUMMARY" or similar
        if re.search(r'THIS\s+BILL\s+SUMMARY', line, re.I):
            in_summary_section = True
            continue
        
        # Stop processing when we leave the summary section 
        if in_summary_section and re.search(r'^[A-Z][A-Z\s]+\$', line):
            if 'Voice' not in line:  # Don't stop on voice line headers
                break
        
        if in_summary_section:
            # Match pattern: (xxx) xxx-xxxx - Description Voice - - - $x.xx
            # Looking specifically for Voice lines with "-" in Plans column
            voice_line_match = re.match(
                r'\((\d{3})\)\s*(\d{3})-(\d{4})\s*-\s*(.*?)\s+Voice\s+(-)\s+(-)\s+(-)\s+\$[\d.]+', 
                line.strip()
            )
            
            if voice_line_match:
                phone_number = ''.join(voice_line_match.group(i) for i in [1, 2, 3])
                description = voice_line_match.group(4).strip()
                
                reason = f"Non-billable voice line ({description})" if description else "Non-billable voice line"
                non_allocatable.append({
                    'number': phone_number,
                    'reason': reason
                })
                print(f"[DEBUG] Detected non-allocatable voice line: {phone_number} - {description}")
    
    return non_allocatable
# %%
def parse_bill(pdf_path: Path) -> BillTotals:
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"

    # -------- basic dates & totals --------
    # Primary pattern: "Bill issue date Mar 03, 2025"
    issue_match = re.search(
        r'Bill issue date[:\s]*([A-Za-z]{3}\s+\d{1,2},\s+\d{4})',
        text,
        re.IGNORECASE,
    )

    # Fallback pattern: "Your bill is due by Mar 24, 2025."
    if not issue_match:
        issue_match = re.search(
            r'Your bill is due by\s+([A-Za-z]{3}\s+\d{1,2},\s+\d{4})',
            text,
            re.IGNORECASE,
        )

    if not issue_match:
        raise ValueError("Could not find bill issue or due date")

    issue_date: date = datetime.strptime(issue_match.group(1), "%b %d, %Y").date()

    # Cycle window: look for the explicit “bill period” phrase first
    cycle_match = re.search(
        r'bill period\s+([A-Za-z]{3}\s+\d{2})\s*[-–]\s*([A-Za-z]{3}\s+\d{2})',
        text, re.I)
    if not cycle_match:
        cycle_match = re.search(
            r'(?:between\s+)?([A-Za-z]{3}\s+\d{2})\s*[-–]\s*([A-Za-z]{3}\s+\d{2})',
            text, re.I)

    if cycle_match:
        start_str, end_str = cycle_match.groups()
        cycle_start = datetime.strptime(f"{start_str} {issue_date.year}", "%b %d %Y").date()
        cycle_end   = datetime.strptime(f"{end_str} {issue_date.year}", "%b %d %Y").date()
        
        # Handle year wraparound (December to January)
        if cycle_end < cycle_start:
            cycle_end = datetime.strptime(f"{end_str} {issue_date.year + 1}", "%b %d %Y").date()
    else:
        # Fallback: treat cycle_end as issue_date, assume 1‑month cycle
        cycle_end = issue_date
        from datetime import timedelta
        cycle_start = (issue_date.replace(day=1)  # first of this month
                       - timedelta(days=1)).replace(day=4)  # approx 4th of prev month

    total_due_match = re.search(r'TOTAL DUE\s*\$?(\d+\.\d{2})', text)
    if not total_due_match:
        raise ValueError("Could not find total due")
    total_due = Decimal(total_due_match.group(1))

    # crude regexes; replace with more robust abstractions if needed
    voice_line = re.search(r'(\d+)\s+VOICE LINES\s*=\s*\$(\d+\.\d{2})', text)
    wear_line  = re.search(r'WEARABLES\s*=\s*\$(\d+\.\d{2})', text)
    conn_line  = re.search(r'CONNECTED DEVICE\S*\s*=\s*\$(\d+\.\d{2})', text)
    
    # Detect non-allocatable voice lines (e.g., "old numbers" during transfers)
    non_allocatable_lines = _detect_non_allocatable_voice_lines(text)
    total_voice_count = int(voice_line.group(1)) if voice_line else 0
    billable_voice_count = total_voice_count - len(non_allocatable_lines)
    
    # Warn about voice line allocation mismatches
    if non_allocatable_lines:
        print(f"⚠️  VOICE LINE TRANSFER DETECTED:")
        print(f"   Total voice lines reported: {total_voice_count}")
        print(f"   Non-allocatable lines (transfers/old numbers): {len(non_allocatable_lines)}")
        for line in non_allocatable_lines:
            print(f"     • {line['number']} - {line['reason']}")
        print(f"   Billable voice lines for allocation: {billable_voice_count}")
        print("   Using billable count for cost allocation calculations.")

    # -------- Netflix charge --------
    netflix_amounts = [Decimal(m)
                       for m in re.findall(r'Netflix[^\n$]{0,120}?\$(\d+\.\d{2})',
                                           text, re.I)]
    netflix_amt = max(netflix_amounts) if netflix_amounts else Decimal(0)
    print(f"[DEBUG] Netflix amounts found → {netflix_amounts}")
    print(f"[DEBUG] Selected netflix_amt = {netflix_amt}")

    # ------------------------------------------------------------------
    # equipment charges – robust section‑based parsing (page 3)
    # ------------------------------------------------------------------
    equip: dict[str, Decimal] = {}
    # Pull text from the first page that contains "EQUIPMENT $"
    equip_page_text = ""
    try:
        with pdfplumber.open(pdf_path) as _pdf:
            for p in _pdf.pages:
                t = p.extract_text()
                if 'EQUIPMENT $' in t:
                    equip_page_text = t
                    break
    except Exception:
        pass

    # Locate the EQUIPMENT block between “EQUIPMENT $” and the next ALL‑CAPS heading
    block = ""
    m_equipment_start = re.search(r'EQUIPMENT\s+\$\d+\.\d{2}', equip_page_text)
    if m_equipment_start:
        start_pos = m_equipment_start.start()
        # End when we hit the next section header like “SERVICES $” or end of page
        m_after = re.search(r'\n[A-Z][A-Z &]+\s+\$\d+\.\d{2}', equip_page_text[m_equipment_start.end():])
        end_pos = m_equipment_start.end() + (m_after.start() if m_after else len(equip_page_text))
        block = equip_page_text[start_pos:end_pos]
        print("\n[DEBUG] Extracted EQUIPMENT block (first 300 chars):")
        print(block[:300].replace("\n", "\\n"))

    if block:
        current_num: str | None = None
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line:
                # blank line breaks the device paragraph
                current_num = None
                continue

            # First line of a device paragraph: contains phone number in parentheses
            phone_match = re.match(r'\((\d{3})\)\s*(\d{3})-(\d{4})', line)
            if phone_match:
                current_num = "".join(phone_match.groups())
                print(f"[DEBUG] Device header line → {current_num}: {line}")
                # Try to capture the first $amount appearing in the header line
                first_money = re.search(r'\$(\d+\.\d{2})', line)
                if first_money:
                    equip[current_num] = Decimal(first_money.group(1))
                    print(f"[DEBUG]  └─ inline amount captured = {equip[current_num]}")
                else:
                    equip[current_num] = None
                continue

            # Subsequent lines while `current_num` is active
            if current_num:
                # Case 2: stand‑alone amount line, e.g.,  "$33.34"
                standalone = re.match(r'^\$(\d+\.\d{2})$', line)
                if standalone:
                    equip[current_num] = Decimal(standalone.group(1))
                    print(f"[DEBUG]  └─ standalone amount captured = {equip[current_num]}")
                    current_num = None  # done with this device
                # Case 3: promo/credit line – ignore, since net is shown in standalone
                # You can extend here if future bills omit the standalone amount
        # Drop entries that never received a monetary amount
        equip = {k: v for k, v in equip.items() if v is not None}
    # ------------------------------------------------------------------

    # international / roaming / long‑distance usage
    usage = {}
    
    # Look for detailed usage charges in CHARGED USAGE section
    usage_block = ""
    m_charged = re.search(r'^\s*CHARGED USAGE\s*$(.*?)(?:OTHER|TAXES|SERVICES|Bill issue date)', text, re.S | re.I | re.M)
    if m_charged:
        usage_block = m_charged.group(1)
        
        # Pattern 1: International calls - "(phone) ... $amount ... to COUNTRY"
        intl_pattern = re.compile(
            r'\((\d{3})\)\s*(\d{3})-(\d{4})'          # phone
            r'[\s\S]{0,120}?'
            r'\$(\d+\.\d{2})'
            r'[\s\S]{0,120}?'
            r'\bto\s+[A-Z]',                          # "to COUNTRY"
            re.I)
        
        for m in intl_pattern.finditer(usage_block):
            num = ''.join(m.group(i) for i in range(1, 4))
            amt = Decimal(m.group(4))
            usage[num] = usage.get(num, Decimal(0)) + amt
        
        # Pattern 2: Domestic usage charges - "(phone) Talk: X mins $amount"
        domestic_pattern = re.compile(
            r'\((\d{3})\)\s*(\d{3})-(\d{4})'          # phone
            r'\s+Talk:\s*\d+\s*mins?\s*'              # "Talk: X mins"
            r'\$(\d+\.\d{2})',                        # amount
            re.I)
        
        for m in domestic_pattern.finditer(usage_block):
            num = ''.join(m.group(i) for i in range(1, 4))
            amt = Decimal(m.group(4))
            usage[num] = usage.get(num, Decimal(0)) + amt

    print(f"[DEBUG] Usage block length = {len(usage_block)} chars")
    print(f"[DEBUG] Parsed usage dict: {usage}")

    return BillTotals(
        cycle_start=cycle_start,
        cycle_end=cycle_end,
        due_date=issue_date,   # bill due date often equals issue date for our needs
        total_due=total_due,
        voice_subtotal=_to_money(voice_line.group(2)),
        voice_line_count=billable_voice_count,  # Use billable count, not raw count
        wearable_subtotal=_to_money(wear_line.group(1)) if wear_line else Decimal(0),
        connected_subtotal=_to_money(conn_line.group(1)) if conn_line else Decimal(0),
        netflix_charge=netflix_amt,
        equipments=equip,
        usage=usage
    )