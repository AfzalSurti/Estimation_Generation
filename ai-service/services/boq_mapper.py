"""
BOQ mapper for civil engineering estimation.

Maps calculated quantity items to SOR detailed rates or Rate Analysis derived rates,
then builds BOQ line items with statutory additions.
"""

import re
from typing import Any, Optional


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", _normalize(text)) if len(w) > 2}


def search_sor_item(description: str, unit: str, sor_items: list[dict]) -> Optional[dict]:
    """
    Find the best matching SOR detailed item by unit and description keywords.

    Prioritises exact unit match, then highest keyword overlap score.
    """
    try:
        desc_tokens = _tokenize(description)
        unit_norm = _normalize(unit)
        best: Optional[dict] = None
        best_score = 0

        for item in sor_items:
            item_unit = _normalize(str(item.get("unit", "")))
            if item_unit and unit_norm and item_unit != unit_norm:
                continue
            item_tokens = _tokenize(str(item.get("description", "")))
            if not item_tokens:
                continue
            overlap = len(desc_tokens & item_tokens)
            if overlap > best_score:
                best_score = overlap
                best = item

        return best if best_score > 0 else None
    except (TypeError, AttributeError):
        return None


def map_quantity_to_rate(
    quantity_item: dict,
    sor_detailed_items: list[dict],
    ra_items: list[dict],
) -> dict[str, Any]:
    """
    Map one quantity row to a rate from SOR or Rate Analysis.

    Returns amount and rate_source (SOR, RA, or RATE_MISSING).
    """
    try:
        description = str(quantity_item.get("description", ""))
        unit = str(quantity_item.get("unit", ""))
        quantity = float(quantity_item.get("quantity", 0))
        item_no = quantity_item.get("item_no", "")

        sor_match = search_sor_item(description, unit, sor_detailed_items)
        if sor_match:
            rate = float(sor_match.get("rate_large_project", sor_match.get("rate", 0)))
            return {
                "item_no": item_no,
                "description": description,
                "quantity": quantity,
                "unit": unit,
                "rate": rate,
                "amount": round(quantity * rate, 2),
                "rate_source": "SOR",
                "sor_item_code": sor_match.get("item_code", ""),
                "sor_reference": f"SOR item {sor_match.get('item_code', '')}",
            }

        desc_norm = _normalize(description)
        for ra in ra_items:
            ra_desc = _normalize(str(ra.get("description", "")))
            ra_unit = _normalize(str(ra.get("unit", "")))
            if ra_unit == _normalize(unit) and (ra_desc in desc_norm or desc_norm in ra_desc):
                rate = float(ra.get("final_rate", 0))
                return {
                    "item_no": item_no,
                    "description": description,
                    "quantity": quantity,
                    "unit": unit,
                    "rate": rate,
                    "amount": round(quantity * rate, 2),
                    "rate_source": "RA",
                    "sor_item_code": ra.get("item_id", ""),
                    "sor_reference": ra.get("sor_reference", ""),
                }

        return {
            "item_no": item_no,
            "description": description,
            "quantity": quantity,
            "unit": unit,
            "rate": 0.0,
            "amount": 0.0,
            "rate_source": "RATE_MISSING",
            "sor_item_code": "",
            "sor_reference": "",
        }
    except (TypeError, ValueError, KeyError) as exc:
        return {
            "item_no": quantity_item.get("item_no", ""),
            "description": quantity_item.get("description", ""),
            "quantity": 0.0,
            "unit": quantity_item.get("unit", ""),
            "rate": 0.0,
            "amount": 0.0,
            "rate_source": "RATE_MISSING",
            "sor_item_code": "",
            "sor_reference": "",
            "error": str(exc),
        }


def generate_boq(
    quantity_sheets: dict,
    sor_detailed_items: list[dict],
    ra_items: list[dict],
) -> dict[str, Any]:
    """
    Map all quantity items to rates and compute group totals.

    Processes road_work flat list and nested structure items.
    """
    boq_items: list[dict] = []
    missing_rates: list[str] = []
    road_work_total = 0.0
    structures_total = 0.0

    try:
        for item in quantity_sheets.get("road_work", []):
            mapped = map_quantity_to_rate(item, sor_detailed_items, ra_items)
            boq_items.append(mapped)
            if mapped["rate_source"] == "RATE_MISSING":
                missing_rates.append(mapped["description"])
            else:
                road_work_total += mapped["amount"]

        for struct in quantity_sheets.get("structures", []):
            for item in struct.get("items", []):
                mapped = map_quantity_to_rate(item, sor_detailed_items, ra_items)
                mapped["structure_id"] = struct.get("structure_id", "")
                mapped["chainage"] = struct.get("chainage", "")
                boq_items.append(mapped)
                if mapped["rate_source"] == "RATE_MISSING":
                    missing_rates.append(mapped["description"])
                else:
                    structures_total += mapped["amount"]

    except (TypeError, KeyError) as exc:
        return {
            "boq_items": boq_items,
            "road_work_total": road_work_total,
            "structures_total": structures_total,
            "grand_total": road_work_total + structures_total,
            "missing_rates": missing_rates,
            "error": str(exc),
        }

    return {
        "boq_items": boq_items,
        "road_work_total": round(road_work_total, 2),
        "structures_total": round(structures_total, 2),
        "grand_total": round(road_work_total + structures_total, 2),
        "missing_rates": missing_rates,
    }


def apply_statutory_additions(
    boq_total: float,
    contingency_pct: float = 3.0,
    labour_cess_pct: float = 1.0,
    gst_pct: float = 18.0,
) -> dict[str, float]:
    """Apply contingency, labour cess, and GST on top of BOQ base total."""
    try:
        base_total = float(boq_total)
        contingency = round(base_total * contingency_pct / 100, 2)
        labour_cess = round(base_total * labour_cess_pct / 100, 2)
        gst = round((base_total + contingency) * gst_pct / 100, 2)
        grand_total = round(base_total + contingency + labour_cess + gst, 2)
        return {
            "base_total": base_total,
            "contingency": contingency,
            "labour_cess": labour_cess,
            "gst": gst,
            "grand_total": grand_total,
        }
    except (TypeError, ValueError):
        return {
            "base_total": 0.0,
            "contingency": 0.0,
            "labour_cess": 0.0,
            "gst": 0.0,
            "grand_total": 0.0,
        }
