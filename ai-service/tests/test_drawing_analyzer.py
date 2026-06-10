import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.drawing_analyzer import analyze_drawing, merge_extractions
from tests.paths import TCS_DRAWING, PLAN_PROFILE_DRAWING


def test_tcs_extraction():
    print("\n" + "=" * 60)
    print("TEST: TCS Extraction")
    print("=" * 60)
    with open(TCS_DRAWING, "rb") as f:
        result = analyze_drawing(f.read(), "TCS.pdf", "road")

    segments = result.get("road_segments", [])
    print(f"Road segments found: {len(segments)}")
    for seg in segments:
        print(f"\n  {seg.get('tcs_type')}")
        print(f"    formation_width_m : {seg.get('formation_width_m')}")
        print(f"    carriageway_width_m: {seg.get('carriageway_width_m')}")
        print(f"    layers            : {seg.get('layers')}")
        print(f"    confidence        : {seg.get('confidence')}")

    assert len(segments) >= 3, f"Expected >= 3 road segments, got {len(segments)}"
    print("\nPASS: test_tcs_extraction")
    return result


def test_pp_extraction():
    print("\n" + "=" * 60)
    print("TEST: P&P Extraction")
    print("=" * 60)
    with open(PLAN_PROFILE_DRAWING, "rb") as f:
        result = analyze_drawing(f.read(), "P&P.pdf", "road")

    structures = result.get("structures", [])
    print(f"Structures found: {len(structures)}")
    for s in structures:
        print(f"\n  {s.get('id')} @ {s.get('chainage')}")
        print(f"    type       : {s.get('type')}")
        print(f"    size       : {s.get('existing_size')}")
        print(f"    action     : {s.get('action')}")
        print(f"    confidence : {s.get('confidence')}")
        if s.get("dia_m"):
            print(f"    dia_m      : {s.get('dia_m')}")
        if s.get("span_m"):
            print(f"    span_m     : {s.get('span_m')} height_m: {s.get('height_m')}")

    assert len(structures) >= 5, f"Expected >= 5 structures, got {len(structures)}"
    print("\nPASS: test_pp_extraction")
    return result


def test_full_pipeline():
    print("\n" + "=" * 60)
    print("TEST: Full Pipeline (TCS + P&P)")
    print("=" * 60)
    with open(TCS_DRAWING, "rb") as f:
        tcs = analyze_drawing(f.read(), "TCS.pdf", "road")
    with open(PLAN_PROFILE_DRAWING, "rb") as f:
        pp = analyze_drawing(f.read(), "P&P.pdf", "road")

    combined = merge_extractions(
        [{"page_num": s.get("page_num"), "tcs_type": s.get("tcs_type"),
          "formation_width_mm": int(s["formation_width_m"] * 1000) if s.get("formation_width_m") else None,
          "carriageway_width_mm": int(s["carriageway_width_m"] * 1000) if s.get("carriageway_width_m") else None,
          "layers": s.get("layers", []), "confidence": s.get("confidence", 0)}
         for s in tcs.get("road_segments", [])],
        [{"chainage": s.get("chainage"), "type": s.get("type"),
          "existing_size": s.get("existing_size"), "proposed_size": s.get("proposed_size"),
          "action": s.get("action"), "confidence": s.get("confidence", 0),
          "page_num": s.get("page_num"), **{k: s[k] for k in ("cells", "span_m", "height_m", "dia_m") if k in s}}
         for s in pp.get("structures", [])],
    )

    print(f"Summary: {len(combined['road_segments'])} road segments, {len(combined['structures'])} structures")
    print(f"Extraction confidence: {combined['extraction_confidence']}")
    print(f"TCS pages parsed: {combined['total_tcs_pages']}")
    print(f"P&P pages parsed: {combined['total_pp_pages']}")
    print("\nPASS: test_full_pipeline")
    return combined


if __name__ == "__main__":
    test_tcs_extraction()
    test_pp_extraction()
    test_full_pipeline()
    print("\n" + "=" * 60)
    print("ALL DRAWING ANALYZER TESTS PASSED")
    print("=" * 60)
