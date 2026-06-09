import pdfplumber
import re
import io
from typing import List, Dict, Optional

KNOWN_UNITS = {
    "cum", "sqm", "mt", "rm", "no", "nos", "kg", "litre", "liter",
    "hour", "day", "tonne", "metre", "each", "ls", "sqmt", "rmt",
    "meter", "km", "quintal", "set", "pair", "cu.m", "sq.m",
}

UNIT_PATTERN = (
    r"(cum|sqm|sq\.m|cu\.m|MT|Rm|No|Nos|Kg|litre|liter|hour|day|tonne|metre|meter|"
    r"each|LS|Hour|Day|Quintal|set|sqmt|rmt|Rmt)"
)

TRANSPORT_KEYWORDS = (
    "carrige of material", "carriage of material", "lead in km", "lead\nin km",
    "cost per trip", "diesel consum", "statement no", "hire charge of truck",
    "avg.speed", "no.of trips", "km done",
)

GARBAGE_DESC_KEYWORDS = (
    "cost per trip", "diesel", "hire charge", "mazdoor", "trips done", "litre of oil",
    "carriage of", "cariage of", "carriage rate", "cariage rate",
    "lead up to", "lead exceeding", "transport of material",
)


def detect_sor_type(text: str) -> str:
    text_lower = text.lower()
    if "national highway" in text_lower:
        return "NH_SOR"
    if "roads and building" in text_lower or "r&b" in text_lower or "r & b" in text_lower:
        return "RB_SOR"
    if "rajpipla" in text_lower or "schedule of rates" in text_lower:
        return "RB_SOR"
    return "UNKNOWN"


def clean_rate(value: str) -> Optional[float]:
    if value is None:
        return None
    cleaned = re.sub(r"(?i)^rs\.?", "", str(value).strip())
    cleaned = re.sub(r"[₹,\s]", "", cleaned)
    try:
        rate = float(cleaned)
        return rate if rate > 0 else None
    except ValueError:
        return None


def normalize_unit(cell: str) -> Optional[str]:
    if not cell:
        return None
    c = re.sub(r"\s+", " ", cell.strip())
    cl = c.lower().rstrip(".")
    mapping = {
        "cum": "cum", "cu.m": "cum", "cu.m.": "cum",
        "sqm": "sqm", "sq.m": "sqm", "sq.m.": "sqm", "sqmt": "sqmt",
        "mt": "MT", "m.t.": "MT",
        "rm": "Rm", "r.m.": "Rm", "rmt": "Rmt",
        "no": "No", "no.": "No", "nos": "Nos", "nos.": "Nos",
        "kg": "Kg", "kg.": "Kg",
        "litre": "litre", "liter": "litre",
        "hour": "Hour", "hr": "Hour",
        "day": "Day",
        "tonne": "tonne", "metre": "metre", "meter": "metre", "mtr": "metre",
        "each": "each", "ls": "LS",
        "quintal": "Quintal", "set": "set", "km": "km",
    }
    return mapping.get(cl)


def is_transport_page(text: str) -> bool:
    t = text.lower()
    return sum(1 for kw in TRANSPORT_KEYWORDS if kw in t) >= 2


def is_base_input_code(cell: str) -> bool:
    cell = cell.strip()
    if re.match(r"^(M-\d+[A-Z]?|L-\d+|P&M\d+)$", cell, re.IGNORECASE):
        return True
    if re.match(r"^M\d{2,4}[A-Z]?$", cell, re.IGNORECASE):
        return True
    return False


def is_pm_related(text: str) -> bool:
    return bool(re.search(r"P\s*&\s*M", text, re.IGNORECASE))


def is_valid_item_code(code: str) -> bool:
    code = code.strip()
    if not code or is_pm_related(code):
        return False
    if re.match(r"^(M-|L-|P&M)", code, re.IGNORECASE):
        return False
    m = re.match(r"^(\d{1,2})\.(\d{1,3})([A-Z](\([a-z0-9]+\))?)?$", code, re.IGNORECASE)
    if not m:
        return False
    chapter = int(m.group(1))
    item = int(m.group(2))
    if chapter < 1 or chapter > 27 or item < 1:
        return False
    if m.group(2) == "00":
        return False
    return True


def rajpipla_code_to_item_code(raw: str) -> Optional[str]:
    raw = raw.strip()
    if is_pm_related(raw) or is_base_input_code(raw):
        return None
    m = re.match(r"^(\d{2})(\d{2,3})([A-Z])?$", raw, re.IGNORECASE)
    if not m:
        return None
    chapter = int(m.group(1))
    item = int(m.group(2))
    if chapter < 1 or chapter > 27 or item < 1:
        return None
    return f"{chapter}.{item}"


def extract_item_code_from_cell(cell: str) -> Optional[str]:
    cell = cell.strip()
    if is_valid_item_code(cell):
        return cell
    return rajpipla_code_to_item_code(cell)


def is_valid_description(desc: str) -> bool:
    if not desc:
        return False
    desc = re.sub(r"\s+", " ", desc.strip())
    if len(desc) < 15:
        return False
    if len(re.findall(r"[A-Za-z]", desc)) < 8:
        return False
    if re.fullmatch(r"[\d\s.,]+", desc):
        return False
    dl = desc.lower()
    if dl in ("above", "below"):
        return False
    if re.match(r"^\d+\.?\d*\s*(above|below)\b", dl):
        return False
    if any(kw in dl for kw in GARBAGE_DESC_KEYWORDS):
        return False
    if is_pm_related(desc):
        return False
    if re.search(r"\b(carriage|cariage)\b", dl):
        return False
    if re.match(r"^c\d{3}[a-z]?\b", dl):
        return False
    if re.match(r"^h\d{3}\b", dl):
        return False
    return True


def preprocess_text(text: str) -> str:
    text = re.sub(r"P\s*&\s*M\s*-\s*\n\s*(\d+)", r"P&M\1", text, flags=re.IGNORECASE)
    text = re.sub(r"P\s*&\s*M\s*-\s*(\d+)", r"P&M\1", text, flags=re.IGNORECASE)
    return text


def parse_sor_pdf(file_bytes: bytes, filename: str) -> Dict:
    base_inputs = []
    detailed_items = []
    failed_pages = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        total_pages = len(pdf.pages)

        sor_type = "UNKNOWN"
        for i in range(min(3, total_pages)):
            sor_type = detect_sor_type(pdf.pages[i].extract_text() or "")
            if sor_type != "UNKNOWN":
                break

        for page_num, page in enumerate(pdf.pages, 1):
            try:
                text = preprocess_text(page.extract_text() or "")
                if is_transport_page(text):
                    continue

                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            if not row:
                                continue
                            base = try_parse_base_input(row, page_num)
                            if base:
                                base_inputs.append(base)
                                continue
                            item = try_parse_detailed_item(row, page_num, sor_type)
                            if item:
                                detailed_items.append(item)
                else:
                    base_inputs.extend(parse_base_from_text(text, page_num))
                    detailed_items.extend(parse_detailed_from_text(text, page_num, sor_type))

            except Exception as e:
                failed_pages.append({"page": page_num, "error": str(e)})

    base_inputs = dedupe_items(base_inputs, ["code", "rate", "description"])
    detailed_items = dedupe_items(detailed_items, ["item_code", "description", "rate_large_project"])

    return {
        "filename": filename,
        "sor_type": sor_type,
        "total_pages": total_pages,
        "base_inputs_found": len(base_inputs),
        "detailed_items_found": len(detailed_items),
        "failed_pages": failed_pages,
        "base_inputs": base_inputs,
        "detailed_items": detailed_items,
    }


def dedupe_items(items: List[Dict], key_fields: List[str]) -> List[Dict]:
    seen = set()
    out = []
    for item in items:
        key = tuple(str(item.get(f, ""))[:80] for f in key_fields)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def try_parse_base_input(row: List, page_num: int) -> Optional[Dict]:
    cleaned = [str(c).strip() if c else "" for c in row]
    cleaned = [c for c in cleaned if c and c.lower() not in ("none", "sl.no.", "code", "description", "unit")]
    if len(cleaned) < 3:
        return None

    code_idx = next((i for i, c in enumerate(cleaned) if is_base_input_code(c)), None)
    if code_idx is None:
        return None

    code = cleaned[code_idx]
    unit = None
    unit_idx = None
    for i, c in enumerate(cleaned):
        u = normalize_unit(c)
        if u:
            unit = u
            unit_idx = i
            break

    rates = []
    for c in cleaned:
        r = clean_rate(c)
        if r is not None:
            rates.append(r)
    if not rates:
        return None
    rate = rates[-1]

    desc_parts = []
    for i, c in enumerate(cleaned):
        if i == code_idx:
            continue
        if i == unit_idx:
            break
        if clean_rate(c) is not None and i > code_idx:
            continue
        if re.fullmatch(r"\d{1,4}", c):
            continue
        if len(c) > 2:
            desc_parts.append(c)
    description = " ".join(desc_parts).strip() or code

    if is_pm_related(description) and not is_base_input_code(code):
        return None

    return {
        "type": "base_input",
        "code": code,
        "description": description,
        "unit": unit or "—",
        "rate": rate,
        "page_number": page_num,
    }


def try_parse_detailed_item(row: List, page_num: int, sor_type: str) -> Optional[Dict]:
    cleaned = [str(c).strip() if c else "" for c in row]
    cleaned = [c for c in cleaned if c and c.lower() not in ("none", "item no.", "descriptions", "summary of rate analysis")]
    if len(cleaned) < 3:
        return None

    if is_pm_related(" ".join(cleaned)):
        return None

    code = None
    code_idx = None
    for i, c in enumerate(cleaned):
        extracted = extract_item_code_from_cell(c)
        if extracted:
            code = extracted
            code_idx = i
            break
    if not code:
        return None

    unit = None
    unit_idx = None
    for i, c in enumerate(cleaned):
        u = normalize_unit(c)
        if u:
            unit = u
            unit_idx = i
            break
    if not unit:
        return None

    desc_parts = []
    for i, c in enumerate(cleaned):
        if i == code_idx:
            continue
        if i == unit_idx:
            break
        if clean_rate(c) is not None:
            continue
        if extract_item_code_from_cell(c):
            continue
        if re.fullmatch(r"(?i)case-[ivx]+", c):
            continue
        if len(c) > 3:
            desc_parts.append(c)
    description = re.sub(r"\s+", " ", " ".join(desc_parts)).strip()
    description = re.sub(r"^0\.00\s+", "", description)

    rates = [clean_rate(c) for c in cleaned[unit_idx + 1:]]
    rates = [r for r in rates if r is not None]
    if not rates:
        return None

    raw_first = cleaned[code_idx]
    if rajpipla_code_to_item_code(raw_first):
        rates = [rates[-1]]

    if not is_valid_item_code(code) or not is_valid_description(description):
        return None
    if is_rate_mistaken_as_code(code, rates[0]):
        return None

    return make_detailed_item(code, description, unit, rates[:3], page_num, sor_type)


def is_rate_mistaken_as_code(code: str, rate: float) -> bool:
    try:
        return abs(float(code) - rate) < 0.02
    except ValueError:
        return False


def make_detailed_item(
    code: str, description: str, unit: str, rates: List[float], page_num: int, sor_type: str
) -> Dict:
    return {
        "type": "detailed_item",
        "sor_type": sor_type,
        "item_code": code,
        "description": description,
        "unit": unit,
        "rate_large_project": rates[0],
        "rate_medium_project": rates[1] if len(rates) > 1 else rates[0],
        "rate_small_project": rates[2] if len(rates) > 2 else rates[0],
        "page_number": page_num,
    }


def parse_base_from_text(text: str, page_num: int) -> List[Dict]:
    items = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or is_pm_related(line):
            continue

        patterns = [
            rf"^(\d+)\s+(M\d{{2,4}}[A-Z]?)\s+(.+?)\s+{UNIT_PATTERN}\s+Rs\.?\s*([\d,]+\.?\d*)",
            rf"^(M-\d+[A-Z]?|L-\d+|P&M\d+)\s+(.+?)\s+{UNIT_PATTERN}\s+Rs\.?\s*([\d,]+\.?\d*)",
            rf"^(\d+)\s+(M\d{{2,4}}[A-Z]?)\s+(.+?)\s+{UNIT_PATTERN}\s+([\d,]+\.?\d*)$",
            rf"^(M-\d+[A-Z]?|L-\d+|P&M\d+)\s+(.+?)\s+{UNIT_PATTERN}\s+([\d,]+\.?\d*)$",
        ]
        for pat in patterns:
            m = re.match(pat, line, re.IGNORECASE)
            if not m:
                continue
            groups = m.groups()
            if re.match(r"^(M-|L-|P&M)", groups[0], re.I):
                code, desc, unit, rate_s = groups[0], groups[1], groups[2], groups[3]
            else:
                code, desc, unit, rate_s = groups[1], groups[2], groups[3], groups[4]
            rate = clean_rate(rate_s)
            nu = normalize_unit(unit)
            if rate and nu and is_base_input_code(code):
                items.append({
                    "type": "base_input",
                    "code": code,
                    "description": desc.strip(),
                    "unit": nu,
                    "rate": rate,
                    "page_number": page_num,
                })
            break
    return items


def parse_detailed_from_text(text: str, page_num: int, sor_type: str) -> List[Dict]:
    items = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or is_pm_related(line):
            continue

        m = re.match(
            rf"^(\d{{1,2}}\.\d{{1,3}}[A-Z]?)\s+(.+?)\s+{UNIT_PATTERN}\s+"
            r"(?:Rs\.?\s*)?([\d,]+\.?\d*)\s*([\d,]+\.?\d*)?\s*([\d,]+\.?\d*)?$",
            line,
            re.IGNORECASE,
        )
        if m:
            code = m.group(1)
            desc = m.group(2).strip()
            unit = normalize_unit(m.group(3))
            rates = [clean_rate(m.group(i)) for i in (4, 5, 6)]
            rates = [r for r in rates if r is not None]
            if (
                is_valid_item_code(code)
                and is_valid_description(desc)
                and unit
                and rates
                and not is_rate_mistaken_as_code(code, rates[0])
            ):
                items.append(make_detailed_item(code, desc, unit, rates, page_num, sor_type))
            continue

        m2 = re.match(
            rf"^(\d{{5}}[A-Z]?)\s+(.+?)\s+{UNIT_PATTERN}\s+([\d,]+\.?\d*)$",
            line,
            re.IGNORECASE,
        )
        if m2:
            code = rajpipla_code_to_item_code(m2.group(1))
            desc = m2.group(2).strip()
            unit = normalize_unit(m2.group(3))
            rate = clean_rate(m2.group(4))
            if code and is_valid_description(desc) and unit and rate:
                items.append(make_detailed_item(code, desc, unit, [rate], page_num, sor_type))

    return items
