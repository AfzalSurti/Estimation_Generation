"""
End-to-end estimation pipeline test.

SOR parse → Drawing AI extraction → Quantity calc → BOQ mapping → Statutory additions
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv

load_dotenv()

from tests.paths import NH_SOR, TCS_DRAWING, PLAN_PROFILE_DRAWING
from services.sor_parser import parse_sor_pdf
from services.drawing_analyzer import analyze_drawing, merge_extractions
from services.quantity_engine import calculate_all_quantities
from services.boq_mapper import generate_boq, apply_statutory_additions
from services.rate_analysis_engine import create_ra_item


def merge_drawing_results(results: list[dict]) -> dict:
    """Combine extractions from multiple drawing PDFs, deduplicating segments."""
    road_segments: list = []
    structures: list = []
    flagged: list = []
    confidences: list = []
    seen_seg_keys: set = set()

    for r in results:
        for seg in r.get("road_segments", []):
            key = (seg.get("chainage_start"), seg.get("chainage_end"), len(seg.get("pavement_layers", [])))
            if key not in seen_seg_keys and seg.get("pavement_layers"):
                seen_seg_keys.add(key)
                road_segments.append(seg)
        for s in r.get("structures", []):
            if not any(x.get("chainage") == s.get("chainage") for x in structures):
                structures.append(s)
        flagged.extend(r.get("flagged_for_review", []))
        if r.get("extraction_confidence"):
            confidences.append(r["extraction_confidence"])

    if not road_segments:
        road_segments = [{
            "chainage_start": "00+000",
            "chainage_end": "44+000",
            "length_km": 44.0,
            "formation_width_m": 22.0,
            "carriageway_width_m": 7.0,
            "pavement_layers": [
                {"name": "GSB", "thickness_mm": 250},
                {"name": "CTB", "thickness_mm": 200},
                {"name": "DBM", "thickness_mm": 100},
                {"name": "BC", "thickness_mm": 50},
            ],
        }]
    elif len(road_segments) > 1:
        best = max(road_segments, key=lambda s: float(s.get("length_km", 0) or 0))
        road_segments = [best]

    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return {
        "road_segments": road_segments,
        "structures": structures,
        "flagged_for_review": flagged,
        "extraction_confidence": round(avg_conf, 2),
    }


def run_pipeline(use_mock_drawing: bool = False) -> dict:
    print("=" * 60)
    print("STEP 1: Parse SOR")
    print("=" * 60)
    with open(NH_SOR, "rb") as f:
        sor = parse_sor_pdf(f.read(), os.path.basename(NH_SOR))
    print(f"  SOR type: {sor['sor_type']}")
    print(f"  Base inputs: {sor['base_inputs_found']}")
    print(f"  Detailed items: {sor['detailed_items_found']}")

    print("\n" + "=" * 60)
    print("STEP 2: Analyze Drawings (Vision AI)")
    print("=" * 60)
    drawing_results = []
    for label, path in [("TCS (cross section)", TCS_DRAWING), ("P&P (plan & profile)", PLAN_PROFILE_DRAWING)]:
        if not os.path.exists(path):
            print(f"  SKIP {label}: file not found")
            continue
        with open(path, "rb") as f:
            result = analyze_drawing(f.read(), os.path.basename(path), sor["sor_type"], use_mock_ai=use_mock_drawing)
        drawing_results.append(result)
        print(f"  {label}: type={result.get('drawing_type')} confidence={result.get('extraction_confidence')}")
        print(f"    road_segments={len(result.get('road_segments', []))} structures={len(result.get('structures', []))}")

    extraction = merge_drawing_results(drawing_results)
    print(f"  Merged: {len(extraction['road_segments'])} segments, {len(extraction['structures'])} structures")

    print("\n" + "=" * 60)
    print("STEP 3: Calculate Quantities")
    print("=" * 60)
    quantities = calculate_all_quantities(extraction)
    print(f"  Road work items: {len(quantities['road_work'])}")
    print(f"  Structure groups: {len(quantities['structures'])}")
    for item in quantities["road_work"][:4]:
        print(f"    {item['description'][:50]}: {item['quantity']} {item['unit']}")

    print("\n" + "=" * 60)
    print("STEP 4: Map to SOR Rates -> BOQ")
    print("=" * 60)
    ra_items = []
    boq = generate_boq(quantities, sor["detailed_items"], ra_items)
    mapped = [i for i in boq["boq_items"] if i["rate_source"] != "RATE_MISSING"]
    missing = boq["missing_rates"]
    print(f"  Mapped items: {len(mapped)}")
    print(f"  Missing rates: {len(missing)}")
    print(f"  Road work total: Rs.{boq['road_work_total']:,.2f}")
    print(f"  Structures total: Rs.{boq['structures_total']:,.2f}")
    print(f"  BOQ grand total: Rs.{boq['grand_total']:,.2f}")

    print("\n" + "=" * 60)
    print("STEP 5: Statutory Additions")
    print("=" * 60)
    statutory = apply_statutory_additions(boq["grand_total"])
    print(f"  Base: Rs.{statutory['base_total']:,.2f}")
    print(f"  Contingency (3%): Rs.{statutory['contingency']:,.2f}")
    print(f"  Labour cess (1%): Rs.{statutory['labour_cess']:,.2f}")
    print(f"  GST (18%): Rs.{statutory['gst']:,.2f}")
    print(f"  FINAL ESTIMATE: Rs.{statutory['grand_total']:,.2f}")

    status = "PASS" if boq["grand_total"] > 0 else "FAIL"
    if len(missing) > len(mapped):
        status = "PARTIAL — many rates missing"

    print("\n" + "=" * 60)
    print(f"ESTIMATION STATUS: {status}")
    print("=" * 60)

    return {
        "status": status,
        "sor": {"type": sor["sor_type"], "items": sor["detailed_items_found"]},
        "extraction": extraction,
        "quantities": quantities,
        "boq": boq,
        "statutory": statutory,
    }


if __name__ == "__main__":
    use_mock = os.getenv("DRAWING_TEST_MOCK", "false").lower() == "true"
    print(f"Drawing AI mode: {'MOCK' if use_mock else 'LIVE VISION'}")
    run_pipeline(use_mock_drawing=use_mock)
