import pdfplumber
import re
import io
from typing import List, Dict

def detect_sor_type(text: str) -> str:
    if "National Highway" in text or "NH" in text:
        return "NH_SOR"
    elif "Roads and Building" in text or "R&B" in text or "R & B" in text:
        return "RB_SOR"
    return "UNKNOWN"

def parse_sor_pdf(file_bytes: bytes, filename: str) -> Dict:
    base_inputs = []
    detailed_items = []
    failed_pages = []
    sor_type = "UNKNOWN"

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        total_pages = len(pdf.pages)

        # Detect SOR type from first page
        first_text = pdf.pages[0].extract_text() or ""
        sor_type = detect_sor_type(first_text)

        for page_num, page in enumerate(pdf.pages, 1):
            try:
                text = page.extract_text() or ""
                tables = page.extract_tables()

                if tables:
                    for table in tables:
                        for row in table:
                            # Try base input first (M-001, L-01, P&M1001)
                            base = parse_base_input_row(row, page_num)
                            if base:
                                base_inputs.append(base)
                                continue
                            # Try detailed item (1.1, 3.4, 5.4 etc)
                            item = parse_detailed_item_row(row, page_num, sor_type)
                            if item:
                                detailed_items.append(item)
                else:
                    # Fallback: raw text parsing
                    base_inputs += parse_base_inputs_from_text(text, page_num)
                    detailed_items += parse_detailed_items_from_text(text, page_num, sor_type)

            except Exception as e:
                failed_pages.append({"page": page_num, "error": str(e)})

    return {
        "filename": filename,
        "sor_type": sor_type,
        "total_pages": total_pages,
        "base_inputs_found": len(base_inputs),
        "detailed_items_found": len(detailed_items),
        "failed_pages": failed_pages,
        "base_inputs": base_inputs,
        "detailed_items": detailed_items
    }


def parse_base_input_row(row: List, page_num: int) -> Dict | None:
    if not row:
        return None
    cleaned = [str(c).strip() if c else "" for c in row]
    cleaned = [c for c in cleaned if c and c.lower() != "none"]
    if len(cleaned) < 3:
        return None

    # Base input codes: M-001, L-01, P&M1001
    code_pattern = re.compile(r'^(M-\d+[A-Z]?|L-\d+|P&M\d+)$')

    code = None
    description = None
    unit = None
    rate = None

    for cell in cleaned:
        if code_pattern.match(cell.strip()) and not code:
            code = cell.strip()
        elif cell.strip() in ["cum", "Cum", "CUM", "sqm", "Sqm", "SQM",
                               "MT", "mt", "Rm", "RM", "No", "Nos", "nos",
                               "Kg", "kg", "KG", "litre", "liter", "hour",
                               "Hour", "day", "Day", "tonne", "Tonne",
                               "metre", "Metre", "Per Tonne Km.", "LS"]:
            unit = cell.strip()
        elif re.match(r'^[\d,]+\.?\d*$', cell.replace(',', '')) and not rate:
            try:
                rate = float(cell.replace(',', ''))
            except:
                pass
        elif len(cell) > 4 and not description:
            description = cell

    if code and rate:
        return {
            "type": "base_input",
            "code": code,
            "description": description or "",
            "unit": unit or "—",
            "rate": rate,
            "page_number": page_num
        }
    return None


def parse_detailed_item_row(row: List, page_num: int, sor_type: str) -> Dict | None:
    if not row:
        return None
    cleaned = [str(c).strip() if c else "" for c in row]
    cleaned = [c for c in cleaned if c and c.lower() != "none"]
    if len(cleaned) < 3:
        return None

    # Detailed item codes: 1.1, 2.3(A), 3.4(i), 15.1 etc
    code_pattern = re.compile(r'^\d+\.\d+[A-Z]?(\([A-Za-z0-9]+\))?$')

    code = None
    description = None
    unit = None
    rate_large = None
    rate_medium = None
    rate_small = None

    for i, cell in enumerate(cleaned):
        if code_pattern.match(cell.strip()) and not code:
            code = cell.strip()
        elif cell.strip() in ["cum", "Cum", "CUM", "sqm", "Sqm", "SQM",
                               "MT", "mt", "Rm", "RM", "No", "Nos", "nos",
                               "Kg", "kg", "metre", "Metre", "tonne",
                               "Tonne", "hour", "Hour", "each", "Each",
                               "LS", "Sqmt", "Rmt", "sqmt"]:
            unit = cell.strip()
        elif re.match(r'^[\d,]+\.?\d*$', cell.replace(',', '')) and not rate_large:
            try:
                rate_large = float(cell.replace(',', ''))
            except:
                pass
        elif re.match(r'^[\d,]+\.?\d*$', cell.replace(',', '')) and rate_large and not rate_medium:
            try:
                rate_medium = float(cell.replace(',', ''))
            except:
                pass
        elif re.match(r'^[\d,]+\.?\d*$', cell.replace(',', '')) and rate_medium and not rate_small:
            try:
                rate_small = float(cell.replace(',', ''))
            except:
                pass
        elif len(cell) > 8 and not description:
            description = cell

    if code and description and rate_large:
        return {
            "type": "detailed_item",
            "sor_type": sor_type,
            "item_code": code,
            "description": description,
            "unit": unit or "—",
            "rate_large_project": rate_large,
            "rate_medium_project": rate_medium or rate_large,
            "rate_small_project": rate_small or rate_large,
            "page_number": page_num
        }
    return None


def parse_base_inputs_from_text(text: str, page_num: int) -> List[Dict]:
    items = []
    lines = text.split('\n')
    # Pattern: M-001 description unit rate
    pattern = re.compile(
        r'^(M-\d+[A-Z]?|L-\d+|P&M\d+)\s+(.+?)\s+'
        r'(cum|sqm|MT|Rm|No|Kg|litre|hour|day|tonne|metre|Nos|each|LS|Hour|Day)\s+'
        r'([\d,]+\.?\d+)$',
        re.IGNORECASE
    )
    for line in lines:
        line = line.strip()
        match = pattern.match(line)
        if match:
            try:
                items.append({
                    "type": "base_input",
                    "code": match.group(1),
                    "description": match.group(2).strip(),
                    "unit": match.group(3),
                    "rate": float(match.group(4).replace(',', '')),
                    "page_number": page_num,
                    "source": "text"
                })
            except:
                pass
    return items


def parse_detailed_items_from_text(text: str, page_num: int, sor_type: str) -> List[Dict]:
    items = []
    lines = text.split('\n')
    # Pattern: 5.4 Description cum 6694.56 6824.28 7032.56
    pattern = re.compile(
        r'^(\d+\.\d+[A-Z]?)\s+(.+?)\s+'
        r'(cum|sqm|MT|Rm|No|Kg|metre|tonne|each|LS|Hour|Nos|sqmt)\s+'
        r'([\d,]+\.?\d+)\s*([\d,]+\.?\d+)?\s*([\d,]+\.?\d+)?$',
        re.IGNORECASE
    )
    for line in lines:
        line = line.strip()
        match = pattern.match(line)
        if match:
            try:
                rate_l = float(match.group(4).replace(',', ''))
                rate_m = float(match.group(5).replace(',', '')) if match.group(5) else rate_l
                rate_s = float(match.group(6).replace(',', '')) if match.group(6) else rate_l
                items.append({
                    "type": "detailed_item",
                    "sor_type": sor_type,
                    "item_code": match.group(1),
                    "description": match.group(2).strip(),
                    "unit": match.group(3),
                    "rate_large_project": rate_l,
                    "rate_medium_project": rate_m,
                    "rate_small_project": rate_s,
                    "page_number": page_num,
                    "source": "text"
                })
            except:
                pass
    return items