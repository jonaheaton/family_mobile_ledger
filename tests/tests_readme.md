# T-Mobile Bill Parser Testing Notes

## PDF Structure

### Equipment Charges Location

- **Page 1**: Only shows the equipment subtotal
- **Page 2**: Contains a summary table repeating the amounts
- **Page 3**: Contains the detailed equipment section (primary source for parsing)

### Equipment Section Format (Page 3)

The detailed equipment charges appear in a specific block:

- Starts with header "EQUIPMENT $59.59"
- Located directly below the bold word "HANDSETS"
- Ends at the next all-caps section header (e.g., "SERVICES")

### Device Entry Format

Each device appears as a mini-paragraph with this structure:

```text
(410) 227-2625 iPhone 15 Pro                                          $33.34
$37.30 installment with $3.96 ...
ID: XXXXX    Remaining balance: $XXX.XX    Installment X of 24

[blank line separates devices]
```

## Parsing Approaches Tried

### 1. Simple Regex on Full Text ❌

- Tried matching `(\d{3})\)\s*(\d{3})-(\d{4}).*?\$(\d+\.\d{2})`
- Failed because it captured too many unrelated numbers and amounts
- Problem: Couldn't distinguish equipment charges from other bill sections

### 2. PDFPlumber Table Extraction ❌

- Used `page.extract_tables()`
- Failed because equipment charges aren't in a proper table format
- Problem: T-Mobile uses space-padding for alignment, not table structures

### 3. Word Position Analysis ❌

- Used `page.extract_words()` to get text with coordinates
- Tried matching amounts to nearest phone numbers based on position
- Failed because vertical spacing wasn't consistent
- Problem: Layout can vary between bills

### 4. Section-Based Parsing (Current Approach) ⚠️

```python
# Find equipment section
sections = text.split('\n\n')
for section in sections:
    if section.strip().startswith('EQUIPMENT $'):
        equipment_section = section
        break

# Process line by line
current_device = None
for line in lines:
    if phone_match:  # Line starts with (XXX) XXX-XXXX
        current_device = number
        amount = extract_end_amount(line)
    elif current_device and ('installment' in line or '$-' in line):
        # Handle installments and credits
```

## Current Issues

1. Not all amounts are being captured correctly
2. Credits and installments might be misattributed
3. Need to handle devices with $0.00 charges properly

## Recommendations for Future Development

### Suggested Approach

1. Focus specifically on page 3
2. Use exact section markers ("EQUIPMENT $" to next all-caps header)
3. Process each device entry as a multi-line unit
4. Track context between lines (current device, installments, credits)
5. Validate total against page 1 subtotal

### Regular Expression Pattern

For device lines, use:

```python
r'^\((\d{3})\)\s*(\d{3})-(\d{4}).*?\$(\d+\.\d{2})\s*$'
```

- Must match start of line (`^`)
- Must capture full phone number
- Must end with amount at end of line (`$`)

### Expected Output

The parser should produce a mapping like:

```python
{
    "4102272625": Decimal("33.34"),
    "2022586292": Decimal("26.25"),
    "8573403847": Decimal("0.00")
}
```

Total should sum to $59.59 (matching page 1 subtotal)

## Test Data

Current test uses June 2025 bill with these expectations:

- Total equipment charges: $59.59
- Three devices:
  1. 410-227-2625: $33.34
  2. 202-258-6292: $26.25
  3. 857-340-3847: $0.00

## Next Steps

1. Add more test fixtures with different bill formats
2. Consider using pdfplumber's table extraction for the summary table on page 2 as a fallback
3. Add validation to ensure parsed amounts match both page 1 subtotal and page 2 summary
4. Add logging to help debug parsing issues
5. Consider splitting the parser into separate methods for each section
