"""
Drawing analyzer for civil engineering BOQ estimation.

Extracts road cross-section and plan/profile data from engineering drawing PDFs
using text-layer regex parsing (no Vision AI).
"""

import re
from typing import Any, Optional


def extract_text_layer(file_bytes: bytes) -> dict:
    import pdfplumber, io
    pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            words = page.extract_words() or []
            pages.append({
                "page_num": i,
                "text": text,
                "word_count": len(words),
                "has_meaningful_text": len(text.strip()) > 50
            })
    return {
        "total_pages": len(pages),
        "pages_with_text": sum(1 for p in pages if p["has_meaningful_text"]),
        "pages": pages
    }


def classify_page_by_text(text: str) -> str:
    """
    Classify a drawing page from its extracted text.

    Returns one of: tcs, plan_profile, title, unknown
    """
    upper = text.upper()
    if len(text.strip()) < 20:
        return "title"
    if (
        "TYPICAL CROSS SECTION" in upper
        or "TCS -" in upper
        or "TCS-" in upper
        or "FORMATION WIDTH" in upper
    ):
        return "tcs"
    if (
        "CULVERT" in upper
        or "CHAINAGE" in upper
        or "SET OUT DATA" in upper
        or "PROP. CENTER LINE" in upper
    ):
        return "plan_profile"
    return "unknown"


_LAYER_NAME_MAP = {
    "BC": "BC",
    "DBM": "DBM",
    "GSB": "GSB",
    "CTB": "CTB",
    "PQC": "PQC",
    "FDR": "FDR",
    "DLC": "DLC",
    "BM": "BM",
    "PRIME COAT": "PRIME COAT",
    "TACK COAT": "TACK COAT",
}


def _normalize_layer_name(raw: str) -> str:
    name = raw.upper().strip()
    for key in _LAYER_NAME_MAP:
        if name.startswith(key):
            return _LAYER_NAME_MAP[key]
    return name.split("-")[0].split("(")[0].strip()


def _extract_layers(text: str) -> list[dict]:
    """Extract pavement layers from TCS page text."""
    layers: list[dict] = []
    seen: set[str] = set()

    pat_thickness_first = re.compile(
        r"(\d{2,3})\s*MM?\s*(?:RECLAMED\s+)?(BC|DBM|GSB|CTB|PQC|FDR|DLC|BM|PRIME COAT|TACK COAT)",
        re.IGNORECASE,
    )
    for match in pat_thickness_first.finditer(text):
        thickness = int(match.group(1))
        name = _normalize_layer_name(match.group(2))
        if name not in seen:
            seen.add(name)
            layers.append({"name": name, "thickness_mm": thickness})

    pat_name_first = re.compile(
        r"(BC|DBM|GSB|CTB|PQC|FDR|DLC|BM)[- ]*\(?GRADING[- ]*[IVX]+\)?\s*(\d{2,3})\s*MM?",
        re.IGNORECASE,
    )
    for match in pat_name_first.finditer(text):
        name = _normalize_layer_name(match.group(1))
        thickness = int(match.group(2))
        if name not in seen:
            seen.add(name)
            layers.append({"name": name, "thickness_mm": thickness})

    return layers


def extract_tcs_chainage_table(text: str) -> list:
    """
    Extract chainage application table from TCS page.

    Returns list of {chainage_from, chainage_to, length_m}
    """
    ranges = []

    chainage_pattern = re.compile(
        r"(\d{2}\+\d{3,4})\s+(\d{2}\+\d{3,4})\s+(\d{2,5})"
    )

    for match in chainage_pattern.finditer(text):
        from_ch = match.group(1)
        to_ch = match.group(2)
        length = int(match.group(3))

        def ch_to_m(ch: str) -> int:
            parts = ch.split("+")
            return int(parts[0]) * 1000 + int(parts[1])

        expected_length = ch_to_m(to_ch) - ch_to_m(from_ch)
        if expected_length < 0:
            from_ch, to_ch = to_ch, from_ch
            expected_length = -expected_length

        if abs(length - expected_length) / max(expected_length, 1) < 0.05:
            ranges.append({
                "chainage_from": from_ch,
                "chainage_to": to_ch,
                "length_m": length,
            })

    return ranges


def _extract_chainage_table_ocr_text(file_bytes: bytes, page_num: int) -> str:
    """
    OCR embedded chainage application table images on TCS pages.

    Chainage tables are rasterized inside the PDF (not in the text layer).
    """
    try:
        import io

        import fitz
        from PIL import Image

        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError:
            return ""

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        if page_num < 1 or page_num > len(doc):
            return ""

        page = doc[page_num - 1]
        ocr = RapidOCR()
        chainage_pattern = re.compile(r"\d{2}\+\d{3,4}")

        for img in page.get_images():
            width, height = img[2], img[3]
            if width < 400 or height < 400:
                continue

            pix = fitz.Pixmap(doc, img[0])
            if pix.n - pix.alpha > 3:
                pix = fitz.Pixmap(fitz.csRGB, pix)

            base_image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

            for rotation in (90, 0, 270):
                rotated = base_image.rotate(rotation, expand=True)
                rot_buffer = io.BytesIO()
                rotated.save(rot_buffer, format="PNG")
                result, _ = ocr(rot_buffer.getvalue())
                candidate = " ".join(item[1] for item in result) if result else ""
                if chainage_pattern.search(candidate) and re.search(r"\d{2,5}", candidate):
                    return candidate

        return ""
    except Exception:
        return ""


def parse_tcs_page(text: str, page_num: int) -> Optional[dict]:
    """
    Extract pavement layer data from a Typical Cross Section page.

    Returns None if no pavement layers are found.
    """
    try:
        layers = _extract_layers(text)
        if not layers:
            return None

        tcs_type = None
        tcs_match = re.search(r"TCS\s*[-–]?\s*(\d+[A-Za-z]?)", text, re.IGNORECASE)
        if tcs_match:
            tcs_type = f"TCS-{tcs_match.group(1).upper()}"

        formation_width_mm = None
        for pat in (
            r"(\d{4,6})\s*\n?\s*FORMATION WIDTH",
            r"FORMATION WIDTH\s*\n?\s*(\d{4,6})",
        ):
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                formation_width_mm = int(m.group(1))
                break

        carriageway_width_mm = _extract_carriageway_width_mm(text)

        confidence = 0.5
        if tcs_type:
            confidence += 0.2
        if formation_width_mm:
            confidence += 0.1
        if len(layers) >= 2:
            confidence += 0.1
        if carriageway_width_mm:
            confidence += 0.1

        chainage_ranges = extract_tcs_chainage_table(text)

        return {
            "page_num": page_num,
            "tcs_type": tcs_type or f"TCS-page-{page_num}",
            "formation_width_mm": formation_width_mm,
            "carriageway_width_mm": carriageway_width_mm,
            "layers": layers,
            "chainage_ranges": chainage_ranges,
            "total_length_m": sum(r["length_m"] for r in chainage_ranges),
            "confidence": round(min(confidence, 1.0), 2),
        }
    except (TypeError, ValueError):
        return None


def _extract_carriageway_width_mm(text: str) -> Optional[int]:
    """
    Find carriageway width in mm from lines containing CARRIAGEWAY.

    Carriageway is typically 5000-9000 mm; numbers appear before the label on the same line.
    """
    lines = text.split("\n")
    candidates: list[int] = []

    for i, line in enumerate(lines):
        if not re.search(r"CARRIAGE\s*WAY", line, re.IGNORECASE):
            continue
        search_lines = [line]
        if i > 0:
            search_lines.insert(0, lines[i - 1])
        if i + 1 < len(lines):
            search_lines.append(lines[i + 1])

        for search_line in search_lines:
            for num_str in re.findall(r"\b(\d{4,5})\b", search_line):
                val = int(num_str)
                if 5000 <= val <= 9000:
                    candidates.append(val)

    if candidates:
        return candidates[0]

    for i, line in enumerate(lines):
        if not re.search(r"CARRIAGE\s*WAY", line, re.IGNORECASE):
            continue
        search_lines = [line]
        if i > 0:
            search_lines.insert(0, lines[i - 1])
        nearby_nums = []
        for search_line in search_lines:
            nearby_nums.extend(int(n) for n in re.findall(r"\b(\d{4,5})\b", search_line))
        in_range = [n for n in nearby_nums if 5000 <= n <= 9000]
        if in_range:
            return max(in_range)

    return None


def _normalize_structure_type(size_str: str) -> str:
    upper = size_str.upper()
    if any(k in upper for k in ("SYPHON", "SHYPHONE", "SHYPOHONE")):
        return "canal_syphon"
    if any(k in upper for k in ("FLYOVER", "ELEVATED")):
        return "flyover"
    if "SUBWAY" in upper:
        return "subway"
    if any(k in upper for k in ("CANAL BRIDGE", "MAJOR BRIDGE")):
        return "major_bridge"
    if any(k in upper for k in ("MNB", "MINOR BRIDGE")):
        return "minor_bridge"
    if any(k in upper for k in ("PIPE CULVERT", "HPC", " NP", "NP ")):
        return "pipe_culvert"
    if "BOX" in upper or "RCC BOX" in upper:
        return "box_culvert"
    if "SLAB" in upper:
        return "slab_culvert"
    if "BRIDGE" in upper:
        return "bridge"
    if "VUP" in upper:
        return "vup"
    if "LUP" in upper:
        return "lup"
    if "ROB" in upper:
        return "rob"
    if "ROU" in upper:
        return "rou"
    return "unknown"


def _parse_dimensions(size_str: str, struct_type: str) -> dict:
    dims: dict[str, Any] = {}
    upper = size_str.upper()

    three_match = re.search(r"(\d+)[Xx](\d+\.?\d*)[Xx](\d+\.?\d*)", size_str)
    if three_match:
        dims["cells"] = int(three_match.group(1))
        dims["span_m"] = float(three_match.group(2))
        dims["height_m"] = float(three_match.group(3))
        return dims

    two_match = re.search(
        r"(\d+)[Xx](\d+\.?\d*)m?\s*(BOX|PIPE|SLAB)",
        size_str,
        re.IGNORECASE,
    )
    if two_match:
        dims["cells"] = int(two_match.group(1))
        val = float(two_match.group(2))
        kind = two_match.group(3).upper()
        if kind == "PIPE":
            dims["dia_m"] = val
        else:
            dims["span_m"] = val
            dims["height_m"] = None
            if kind == "BOX":
                dims["needs_height_review"] = True
        return dims

    fallback = re.search(r"(\d+)[Xx](\d+\.?\d*)\s*m?", size_str, re.IGNORECASE)
    if fallback:
        dims["cells"] = int(fallback.group(1))
        val = float(fallback.group(2))
        if struct_type == "pipe_culvert":
            dims["dia_m"] = val
        else:
            dims["span_m"] = val
            if struct_type == "box_culvert":
                dims["height_m"] = None
                dims["needs_height_review"] = True
    return dims


def _apply_pipe_diameter_sanity(entry: dict) -> dict:
    """Reclassify pipe culverts with impossible diameter (> 2.5 m) as box culverts."""
    dia = entry.get("dia_m")
    if entry.get("type") == "pipe_culvert" and dia is not None and dia > 2.5:
        entry["type"] = "box_culvert"
        entry["span_m"] = dia
        entry["dia_m"] = None
        entry["height_m"] = None
        entry["needs_review"] = True
        entry["needs_height_review"] = True
    return entry


def _clean_dash_value(value: str) -> Optional[str]:
    cleaned = value.strip()
    if not cleaned or re.fullmatch(r"[-–\s]+", cleaned):
        return None
    return cleaned


def _structure_completeness_score(item: dict) -> int:
    """Score how complete a structure record is (higher = more fields populated)."""
    score = 0
    for key in ("type", "existing_size", "raw_type", "raw_span", "cells", "span_m", "height_m", "dia_m", "action"):
        val = item.get(key)
        if val is not None and val != "" and val != "unknown":
            score += 1
    if item.get("source") == "culvert_bridge_detail":
        score += 1
    return score


def _pick_better_structure(a: dict, b: dict) -> dict:
    """Choose the more complete structure when deduplicating by chainage."""
    conf_a = float(a.get("confidence", 0))
    conf_b = float(b.get("confidence", 0))
    if conf_a != conf_b:
        return a if conf_a > conf_b else b
    return a if _structure_completeness_score(a) >= _structure_completeness_score(b) else b


def parse_type_chainage_span_blocks(text: str, page_num: int) -> list[dict]:
    """
    Extract structures from TYPE/CHAINAGE/SPAN annotation blocks
    in the profile section of P&P pages.
    These are more reliably extracted than the CULVERT/BRIDGE DETAIL blocks.
    """
    results: list[dict] = []
    seen_chainages: set[str] = set()

    profile_sections = re.split(r"ANKLESHWAR\s+RAJPIPLA", text, flags=re.IGNORECASE)

    for section in profile_sections[1:]:
        profile = section[:1200]

        types = re.findall(
            r"TYPE\s*:\s*(HPC|BOX CULVERT|MNB|MJB|CANAL SYPHON|CANAL BRIDGE|PIPE CULVERT|SLAB CULVERT)",
            profile,
            re.IGNORECASE,
        )
        chainages = re.findall(
            r"(?<!EXISTING )(?<!PROPOSED )(?:PROP\.\s*LME\s+)?CHAINAGE\s*:\s*(\d+\+\d+)",
            profile,
            re.IGNORECASE,
        )
        spans = re.findall(
            r"SPAN\s*:\s*(\d+[Xx]\d+\.?\d*\s*m?(?:\s*[Øø])?)",
            profile,
            re.IGNORECASE,
        )
        spans = [s.strip() for s in spans if s.strip() and not re.fullmatch(r"[-–\s]+", s.strip())]

        count = max(len(types), len(chainages), len(spans))
        for i in range(count):
            if i >= len(chainages):
                break
            chainage = chainages[i]
            if chainage in seen_chainages:
                continue

            type_str = types[i].strip() if i < len(types) else "UNKNOWN"
            span_str = spans[i].strip() if i < len(spans) else ""

            structure: dict[str, Any] = {
                "chainage": chainage,
                "raw_type": type_str,
                "raw_span": span_str,
                "existing_size": f"{span_str} {type_str}".strip(),
                "source": "type_chainage_span",
                "page_num": page_num,
                "confidence": 0.9,
                "action": "RETAIN",
            }

            type_upper = type_str.upper()
            if "BOX CULVERT" in type_upper or ("BOX" in type_upper and "BRIDGE" not in type_upper):
                structure["type"] = "box_culvert"
            elif "HPC" in type_upper or "PIPE CULVERT" in type_upper:
                structure["type"] = "pipe_culvert"
            elif "MJB" in type_upper or "MAJOR" in type_upper:
                structure["type"] = "major_bridge"
            elif "MNB" in type_upper or "MINOR" in type_upper:
                structure["type"] = "minor_bridge"
            elif "CANAL BRIDGE" in type_upper:
                structure["type"] = "major_bridge"
            elif "CANAL SYPHON" in type_upper or "SYPHON" in type_upper:
                structure["type"] = "canal_syphon"
            else:
                structure["type"] = "unknown"

            dim_match = re.match(r"(\d+)[Xx](\d+\.?\d*)", span_str)
            if dim_match:
                structure["cells"] = int(dim_match.group(1))
                val = float(dim_match.group(2))
                if structure["type"] == "pipe_culvert":
                    structure["dia_m"] = val
                else:
                    structure["span_m"] = val
                    structure["height_m"] = None
                    structure["needs_height_review"] = True

            structure = _apply_pipe_diameter_sanity(structure)
            seen_chainages.add(chainage)
            results.append(structure)

    strict_pattern = re.compile(
        r"TYPE\s*:\s*([^\n]+)\n"
        r"CHAINAGE\s*:\s*([\d+]+)\n"
        r"SPAN\s*:\s*([^\n]+)",
        re.IGNORECASE,
    )
    for match in strict_pattern.finditer(text):
        chainage = match.group(2).strip()
        if chainage in seen_chainages:
            continue
        type_str = match.group(1).strip()
        span_str = match.group(3).strip()

        structure = {
            "chainage": chainage,
            "raw_type": type_str,
            "raw_span": span_str,
            "existing_size": f"{span_str} {type_str}",
            "source": "type_chainage_span",
            "page_num": page_num,
            "confidence": 0.9,
            "action": "RETAIN",
        }
        type_upper = type_str.upper()
        if "BOX" in type_upper:
            structure["type"] = "box_culvert"
        elif "HPC" in type_upper or "PIPE" in type_upper:
            structure["type"] = "pipe_culvert"
        elif "MNB" in type_upper:
            structure["type"] = "minor_bridge"
        elif "MJB" in type_upper or "CANAL BRIDGE" in type_upper:
            structure["type"] = "major_bridge"
        elif "SYPHON" in type_upper:
            structure["type"] = "canal_syphon"
        else:
            structure["type"] = "unknown"

        dim_match = re.match(r"(\d+)[Xx](\d+\.?\d*)", span_str)
        if dim_match:
            structure["cells"] = int(dim_match.group(1))
            val = float(dim_match.group(2))
            if structure["type"] == "pipe_culvert":
                structure["dia_m"] = val
            else:
                structure["span_m"] = val
                structure["height_m"] = None
                structure["needs_height_review"] = True

        structure = _apply_pipe_diameter_sanity(structure)
        seen_chainages.add(chainage)
        results.append(structure)

    return results


def _parse_culvert_bridge_detail_blocks(text: str, page_num: int) -> list[dict]:
    """Extract structures from CULVERT/BRIDGE DETAIL blocks."""
    results: list[dict] = []

    block_pattern = re.compile(
        r"CULVERT/BRIDGE DETAIL\s*\(\s*(RETAIN|NEW|RECONSTRUCT|WIDEN)\s*\)"
        r"(.*?)(?=CULVERT/BRIDGE DETAIL|$)",
        re.IGNORECASE | re.DOTALL,
    )

    for block_match in block_pattern.finditer(text):
        action = block_match.group(1).upper()
        block = block_match.group(2)

        chainage_match = re.search(
            r"EXISTING CHAINAGE:\s*(\d+\+\d+(?:\.\d+)?)",
            block,
            re.IGNORECASE,
        )
        if not chainage_match:
            continue
        chainage = chainage_match.group(1)

        size_match = re.search(
            r"EXIST\.\s*SIZE\s*&\s*TYPE:\s*([^\n]+)",
            block,
            re.IGNORECASE,
        )
        existing_size = size_match.group(1).strip() if size_match else "UNKNOWN"

        proposed_chainage = None
        prop_ch_match = re.search(
            r"PROPOSED CHAINAGE:\s*([^\n]+)",
            block,
            re.IGNORECASE,
        )
        if prop_ch_match:
            proposed_chainage = _clean_dash_value(prop_ch_match.group(1))

        proposed_size = None
        prop_size_match = re.search(
            r"PROP\.\s*SIZE\s*&\s*TYPE:\s*([^\n]+)",
            block,
            re.IGNORECASE,
        )
        if prop_size_match:
            proposed_size = _clean_dash_value(prop_size_match.group(1))

        struct_type = _normalize_structure_type(existing_size)
        dims = _parse_dimensions(existing_size, struct_type)

        confidence = 0.85 if "CULVERT" in existing_size.upper() else 0.7

        entry: dict[str, Any] = {
            "chainage": chainage,
            "type": struct_type,
            "existing_size": existing_size,
            "proposed_size": proposed_size,
            "proposed_chainage": proposed_chainage,
            "action": action,
            "confidence": confidence,
            "page_num": page_num,
            "source": "culvert_bridge_detail",
        }
        entry.update(dims)
        entry = _apply_pipe_diameter_sanity(entry)
        results.append(entry)

    return results


def parse_pp_page(text: str, page_num: int) -> list[dict]:
    """
    Extract culvert/bridge records from a Plan & Profile page.

    Uses CULVERT/BRIDGE DETAIL blocks and TYPE/CHAINAGE/SPAN profile annotations.
    """
    try:
        detail_results = _parse_culvert_bridge_detail_blocks(text, page_num)
        span_results = parse_type_chainage_span_blocks(text, page_num)

        by_chainage: dict[str, dict] = {}
        for item in detail_results + span_results:
            chainage = item.get("chainage", "")
            if not chainage:
                continue
            existing = by_chainage.get(chainage)
            if existing is None:
                by_chainage[chainage] = item
            else:
                by_chainage[chainage] = _pick_better_structure(item, existing)

        return list(by_chainage.values())

    except (TypeError, ValueError):
        return []


def merge_extractions(tcs_results: list[dict], pp_results: list[dict]) -> dict[str, Any]:
    """
    Combine TCS and P&P parse results into a final DrawingExtraction dict.

    Deduplicates structures by chainage, keeping the higher-confidence record.
    """
    road_segments: list[dict] = []
    for tcs in tcs_results:
        fw = tcs.get("formation_width_mm")
        cw = tcs.get("carriageway_width_mm")
        road_segments.append({
            "tcs_type": tcs.get("tcs_type"),
            "formation_width_m": round(fw / 1000, 2) if fw else None,
            "carriageway_width_m": round(cw / 1000, 2) if cw else None,
            "pavement_layers": tcs.get("layers", []),
            "layers": tcs.get("layers", []),
            "chainage_ranges": tcs.get("chainage_ranges", []),
            "total_length_m": tcs.get("total_length_m", 0),
            "confidence": tcs.get("confidence", 0.0),
            "page_num": tcs.get("page_num"),
        })

    structures_by_chainage: dict[str, dict] = {}

    for item in pp_results:
        chainage = item.get("chainage", "")
        if not chainage:
            continue
        existing = structures_by_chainage.get(chainage)
        if existing is None:
            structures_by_chainage[chainage] = item
        else:
            structures_by_chainage[chainage] = _pick_better_structure(item, existing)

    def _chainage_sort_key(s: dict) -> tuple:
        ch = s.get("chainage", "0+0")
        if "+" in ch:
            parts = ch.split("+", 1)
            try:
                return (int(parts[0]), float(parts[1]))
            except ValueError:
                pass
        return (0, 0)

    sorted_items = sorted(structures_by_chainage.values(), key=_chainage_sort_key)

    prefix_map = {
        "pipe_culvert": "PC",
        "box_culvert": "BC",
        "slab_culvert": "SC",
        "bridge": "BR",
        "minor_bridge": "MB",
        "major_bridge": "MJ",
        "canal_syphon": "CS",
        "vup": "VU",
        "lup": "LU",
        "rob": "RB",
        "rou": "RO",
        "flyover": "FO",
        "subway": "SW",
    }
    id_counters: dict[str, int] = {}
    structures: list[dict] = []
    for item in sorted_items:
        stype = item.get("type", "unknown")
        prefix = prefix_map.get(stype, "ST")
        id_counters[prefix] = id_counters.get(prefix, 0) + 1
        struct_id = f"{prefix}-{id_counters[prefix]:03d}"

        entry: dict[str, Any] = {
            "id": struct_id,
            "type": stype,
            "chainage": item.get("chainage"),
            "action": item.get("action"),
            "confidence": item.get("confidence", 0.0),
            "existing_size": item.get("existing_size"),
            "proposed_size": item.get("proposed_size"),
            "page_num": item.get("page_num"),
            "source": item.get("source"),
        }
        for key in ("cells", "span_m", "height_m", "dia_m", "length_m", "raw_type", "raw_span"):
            if key in item:
                entry[key] = item[key]
        for flag in ("needs_height_review", "needs_review"):
            if item.get(flag):
                entry[flag] = True
        structures.append(entry)

    all_confidences = [t.get("confidence", 0) for t in tcs_results] + [s.get("confidence", 0) for s in pp_results]
    avg_conf = round(sum(all_confidences) / len(all_confidences), 2) if all_confidences else 0.0

    return {
        "drawing_type": "typical_cross_section" if tcs_results else "plan_view",
        "road_segments": road_segments,
        "structures": structures,
        "total_tcs_pages": len(tcs_results),
        "total_pp_pages": len({p.get("page_num") for p in pp_results}),
        "extraction_confidence": avg_conf,
        "confidence": avg_conf,
        "flagged_for_review": [],
    }


def analyze_drawing(file_bytes: bytes, filename: str, estimation_type: str) -> dict[str, Any]:
    """
    Main entry point: extract text, classify pages, parse TCS/P&P data, merge.

    Called by the drawing router. Uses regex on PDF text layer only.
    """
    try:
        text_layer = extract_text_layer(file_bytes)
        tcs_results: list[dict] = []
        pp_results: list[dict] = []

        for page in text_layer.get("pages", []):
            text = page.get("text", "")
            page_num = page.get("page_num", 0)
            page_type = classify_page_by_text(text)

            if page_type == "tcs":
                ocr_text = _extract_chainage_table_ocr_text(file_bytes, page_num)
                parsed = parse_tcs_page(f"{text}\n{ocr_text}", page_num)
                if parsed:
                    tcs_results.append(parsed)
            elif page_type == "plan_profile":
                pp_results.extend(parse_pp_page(text, page_num))

        merged = merge_extractions(tcs_results, pp_results)
        merged["filename"] = filename
        merged["estimation_type"] = estimation_type
        merged["total_pages"] = text_layer.get("total_pages", 0)
        merged["pages_with_text"] = text_layer.get("pages_with_text", 0)
        return merged

    except Exception as exc:
        return {
            "filename": filename,
            "estimation_type": estimation_type,
            "drawing_type": "unknown",
            "road_segments": [],
            "structures": [],
            "total_tcs_pages": 0,
            "total_pp_pages": 0,
            "extraction_confidence": 0.0,
            "confidence": 0.0,
            "flagged_for_review": [{"reason": str(exc)}],
            "error": str(exc),
        }
