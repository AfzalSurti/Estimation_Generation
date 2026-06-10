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
        tcs_match = re.search(r"TCS\s*[-–]?\s*(\d+)", text, re.IGNORECASE)
        if tcs_match:
            tcs_type = f"TCS-{tcs_match.group(1)}"

        formation_width_mm = None
        for pat in (
            r"(\d{4,6})\s*\n?\s*FORMATION WIDTH",
            r"FORMATION WIDTH\s*\n?\s*(\d{4,6})",
        ):
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                formation_width_mm = int(m.group(1))
                break

        carriageway_width_mm = None
        cw_matches = re.findall(
            r"(\d{4,5})\s*\n?\s*(?:PAVED\s+)?CARRIAGE\s*WAY",
            text,
            re.IGNORECASE,
        )
        if cw_matches:
            carriageway_width_mm = int(cw_matches[0])

        confidence = 0.5
        if tcs_type:
            confidence += 0.2
        if formation_width_mm:
            confidence += 0.1
        if len(layers) >= 2:
            confidence += 0.1
        if carriageway_width_mm:
            confidence += 0.1

        return {
            "page_num": page_num,
            "tcs_type": tcs_type or f"TCS-page-{page_num}",
            "formation_width_mm": formation_width_mm,
            "carriageway_width_mm": carriageway_width_mm,
            "layers": layers,
            "confidence": round(min(confidence, 1.0), 2),
        }
    except (TypeError, ValueError):
        return None


def _normalize_structure_type(size_str: str) -> str:
    upper = size_str.upper()
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
    if "ROB" in upper or "ROU" in upper:
        return "rob"
    return "unknown"


def _parse_dimensions(size_str: str, struct_type: str) -> dict:
    dims: dict[str, Any] = {}
    box_match = re.search(r"(\d+)[Xx](\d+\.?\d*)[Xx](\d+\.?\d*)", size_str)
    if box_match:
        dims["cells"] = int(box_match.group(1))
        dims["span_m"] = float(box_match.group(2))
        dims["height_m"] = float(box_match.group(3))
        return dims

    two_match = re.search(r"(\d+)[Xx](\d+\.?\d*)\s*m?", size_str, re.IGNORECASE)
    if two_match:
        dims["cells"] = int(two_match.group(1))
        val = float(two_match.group(2))
        if struct_type == "pipe_culvert":
            dims["dia_m"] = val
        else:
            dims["span_m"] = val
    return dims


def _clean_dash_value(value: str) -> Optional[str]:
    cleaned = value.strip()
    if not cleaned or re.fullmatch(r"[-–\s]+", cleaned):
        return None
    return cleaned


def parse_pp_page(text: str, page_num: int) -> list[dict]:
    """
    Extract culvert/bridge records from a Plan & Profile page.

    Returns a list of structure dicts (may be empty).
    """
    results: list[dict] = []

    try:
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
            }
            entry.update(dims)
            results.append(entry)

    except (TypeError, ValueError):
        return results

    return results


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
            "confidence": tcs.get("confidence", 0.0),
            "page_num": tcs.get("page_num"),
        })

    structures_by_chainage: dict[str, dict] = {}

    for item in pp_results:
        chainage = item.get("chainage", "")
        if not chainage:
            continue
        existing = structures_by_chainage.get(chainage)
        if existing and existing.get("confidence", 0) >= item.get("confidence", 0):
            continue
        structures_by_chainage[chainage] = item

    prefix_map = {
        "pipe_culvert": "PC",
        "box_culvert": "BC",
        "slab_culvert": "SC",
        "bridge": "BR",
    }
    id_counters: dict[str, int] = {}
    structures: list[dict] = []
    for item in structures_by_chainage.values():
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
        }
        for key in ("cells", "span_m", "height_m", "dia_m", "length_m"):
            if key in item:
                entry[key] = item[key]
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
                parsed = parse_tcs_page(text, page_num)
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
