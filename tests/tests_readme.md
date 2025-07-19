    # ------------------------------------------------------------------
    # equipment charges – robust section‑based parsing (page 3)
    # ------------------------------------------------------------------
    equip: dict[str, Decimal] = {}
    try:
        with pdfplumber.open(pdf_path) as _pdf:
            if len(_pdf.pages) >= 3:
                page3_text = _pdf.pages[2].extract_text()  # page index starts at 0
            else:
                page3_text = ""
    except Exception:
        page3_text = ""

    # Locate the EQUIPMENT block between “EQUIPMENT $” and the next ALL‑CAPS heading
    block = ""
    m_equipment_start = re.search(r'EQUIPMENT\s+\$\d+\.\d{2}', page3_text)
    if m_equipment_start:
        start_pos = m_equipment_start.start()
        # End when we hit the next section header like “SERVICES $” or end of page
        m_after = re.search(r'\n[A-Z][A-Z &]+\s+\$\d+\.\d{2}', page3_text[m_equipment_start.end():])
        end_pos = m_equipment_start.end() + (m_after.start() if m_after else len(page3_text))
        block = page3_text[start_pos:end_pos]

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
                # Case 1: amount appears at end of same line
                tail_money = re.search(r'\$(\d+\.\d{2})\s*$', line)
                if tail_money:
                    equip[current_num] = Decimal(tail_money.group(1))
                else:
                    # Wait for a subsequent stand‑alone amount line
                    equip[current_num] = None
                continue

            # Subsequent lines while `current_num` is active
            if current_num:
                # Case 2: stand‑alone amount line, e.g.,  "$33.34"
                standalone = re.match(r'^\$(\d+\.\d{2})$', line)
                if standalone:
                    equip[current_num] = Decimal(standalone.group(1))
                    current_num = None  # done with this device
                # Case 2‑b: first positive dollar figure on the next line
                if equip.get(current_num) is None:
                    any_money = re.search(r'\$(\d+\.\d{2})', line)
                    neg_money = re.search(r'\$-\d+\.\d{2}', line)
                    if any_money and not neg_money:
                        equip[current_num] = Decimal(any_money.group(1))
                        current_num = None
                # Case 3: promo/credit line – ignore, since net is shown in standalone
                # You can extend here if future bills omit the standalone amount
        # Replace any None placeholders with 0.00
        for k, v in equip.items():
            if v is None:
                equip[k] = Decimal("0.00")
    # ------------------------------------------------------------------
