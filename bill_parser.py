import pdfplumber, re
from decimal import Decimal
from pathlib import Path
from .datatypes import BillTotals
from datetime import datetime, date

_MONEY = re.compile(r'\$?(-?\d+\.\d{2})')

def _to_money(s: str) -> Decimal:
    return Decimal(_MONEY.search(s).group(1))

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

    # Cycle window  e.g. "between Feb 04 and Mar 03"
    # Cycle window appears as "Jun 04 - Jul 03"
    cycle_match = re.search(r'(?:between\s+)?([A-Za-z]{3}\s+\d{2})\s*[-–]\s*([A-Za-z]{3}\s+\d{2})', text, re.IGNORECASE)
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
    voice_line = re.search(r'VOICE LINES\s*=\s*\$(\d+\.\d{2})', text)
    wear_line  = re.search(r'WEARABLES\s*=\s*\$(\d+\.\d{2})', text)
    conn_line  = re.search(r'CONNECTED DEVICE\S*\s*=\s*\$(\d+\.\d{2})', text)
    netflix    = re.search(r'Netflix.*?(\$?\d+\.\d{2})', text)

    # equipment charges - parse from the detailed section on page 3
    equip = {}
    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) >= 3:
            text = pdf.pages[2].extract_text()
            
            # Find the equipment section
            equipment_section = None
            if 'EQUIPMENT $' in text:
                sections = text.split('\n\n')  # Split on double newlines to separate blocks
                for section in sections:
                    if section.strip().startswith('EQUIPMENT $'):
                        equipment_section = section
                        break
            
            if equipment_section:
                # Process each line in the equipment section
                lines = equipment_section.split('\n')
                current_device = None
                for line in lines:
                    line = line.strip()
                    if not line:
                        current_device = None
                        continue
                        
                    # Match device lines that start with a phone number
                    phone_match = re.search(r'\((\d{3})\)\s*(\d{3})-(\d{4})', line)
                    if phone_match:
                        current_device = ''.join(phone_match.groups())
                        # Look for the amount at the end of this line
                        amount_match = re.search(r'\$(\d+\.\d{2})\s*$', line)
                        if amount_match:
                            equip[current_device] = Decimal(amount_match.group(1))
                        else:
                            equip[current_device] = Decimal('0.00')
                    
                    # Look for installment amounts and credits
                    elif current_device:
                        if 'installment' in line.lower():
                            amount_match = re.search(r'\$(\d+\.\d{2})', line)
                            if amount_match:
                                equip[current_device] = Decimal(amount_match.group(1))
                        elif '$-' in line:
                            credit_match = re.search(r'\$-(\d+\.\d{2})', line)
                            if credit_match:
                                credit = Decimal(credit_match.group(1))
                                equip[current_device] -= credit

    # international/roaming usage
    usage = {}
    for m in re.finditer(r'INTL.*?\((\d{3})[)\s-]*(\d{3})[- ](\d{4}).+?(\$?-?\d+\.\d{2})', text):
        num = ''.join(m.groups()[:3])
        amt = _to_money(m.group(4))
        usage[num] = usage.get(num, Decimal(0)) + amt

    return BillTotals(
        cycle_start=cycle_start,
        cycle_end=cycle_end,
        due_date=issue_date,   # bill due date often equals issue date for our needs
        total_due=total_due,
        voice_subtotal=_to_money(voice_line.group(1)),
        wearable_subtotal=_to_money(wear_line.group(1)) if wear_line else Decimal(0),
        connected_subtotal=_to_money(conn_line.group(1)) if conn_line else Decimal(0),
        netflix_charge=_to_money(netflix.group(1)) if netflix else Decimal(0),
        equipments=equip,
        usage=usage
    )