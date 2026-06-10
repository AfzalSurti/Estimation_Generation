"""
Validation test: hardcoded TCS extraction → quantities → BOQ → estimate.

Compares computed road-work estimate against known project parameters.
No drawing PDFs required.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.sor_parser import parse_sor_pdf
from tests.paths import RAJPIPLA_SOR, NH_SOR

PROJECT_NAME = "Resurfacing and FDR work, Ankleshwar-Rajpipla"
CHAINAGE = "44+000 to 62+450"
TOTAL_PROJECT_LENGTH_M = 18450

TCS_DATA = [
    {
        "tcs_type": "TCS-1",
        "formation_width_m": 21.5,
        "carriageway_width_m": 7.0,
        "layers": [
            {"name": "BC", "thickness_mm": 40},
            {"name": "DBM", "thickness_mm": 50},
        ],
        "total_length_m": 9671,
    },
    {
        "tcs_type": "TCS-1A",
        "formation_width_m": 21.0,
        "carriageway_width_m": 7.0,
        "layers": [
            {"name": "BC", "thickness_mm": 40},
            {"name": "DBM", "thickness_mm": 50},
        ],
        "total_length_m": 4884,
    },
    {
        "tcs_type": "TCS-2",
        "formation_width_m": 21.5,
        "carriageway_width_m": 7.0,
        "layers": [
            {"name": "BC", "thickness_mm": 40},
            {"name": "DBM", "thickness_mm": 50},
        ],
        "total_length_m": 600,
    },
    {
        "tcs_type": "TCS-2A",
        "formation_width_m": 21.0,
        "carriageway_width_m": 7.0,
        "layers": [
            {"name": "BC", "thickness_mm": 40},
            {"name": "DBM", "thickness_mm": 50},
        ],
        "total_length_m": 555,
    },
    {
        "tcs_type": "TCS-3",
        "formation_width_m": 20.61,
        "carriageway_width_m": 7.0,
        "layers": [
            {"name": "PQC", "thickness_mm": 300},
            {"name": "CTB", "thickness_mm": 300},
        ],
        "total_length_m": 500,
    },
    {
        "tcs_type": "TCS-4",
        "formation_width_m": 21.5,
        "carriageway_width_m": 7.0,
        "layers": [
            {"name": "BC", "thickness_mm": 40},
            {"name": "DBM", "thickness_mm": 50},
            {"name": "CTB", "thickness_mm": 300},
        ],
        "total_length_m": 400,
    },
    {
        "tcs_type": "TCS-4A",
        "formation_width_m": 21.0,
        "carriageway_width_m": 7.0,
        "layers": [
            {"name": "BC", "thickness_mm": 40},
            {"name": "DBM", "thickness_mm": 50},
            {"name": "CTB", "thickness_mm": 300},
        ],
        "total_length_m": 900,
    },
    {
        "tcs_type": "TCS-5",
        "formation_width_m": 21.0,
        "carriageway_width_m": 7.0,
        "layers": [
            {"name": "BC", "thickness_mm": 40},
            {"name": "DBM", "thickness_mm": 50},
        ],
        "total_length_m": 310,
    },
    {
        "tcs_type": "TCS-6",
        "formation_width_m": 21.5,
        "carriageway_width_m": 7.0,
        "layers": [
            {"name": "BC", "thickness_mm": 40},
            {"name": "DBM", "thickness_mm": 120},
            {"name": "GSB", "thickness_mm": 125},
        ],
        "total_length_m": 630,
    },
]

LAYER_DESCRIPTIONS = {
    "BC": "Bituminous Concrete",
    "DBM": "Dense Bituminous Macadam",
    "GSB": "Granular Sub Base",
    "CTB": "Cement Treated Base",
    "PQC": "Pavement Quality Concrete",
    "WMM": "Wet Mix Macadam",
}

LAYER_SEARCH_TERMS = {
    "BC": ["bituminous concrete", "recycling of bituminous pavement", "premixed bitumin"],
    "DBM": ["dense bituminous macadam", "bituminous macadam", "dbm"],
    "GSB": ["granular sub base", "gsb"],
    "CTB": ["cement treated base", "cement treated soil", "ctb"],
    "PQC": ["pavement quality concrete", "cement concrete wearing coat", "pqc"],
    "WMM": ["wet mix macadam", "wmm"],
}

SOR_SKIP_KEYWORDS = (
    "rolling and consolidation",
    "labour charges",
    "painting",
    "primning coat",
    "road marking",
    "joint filler",
)

REAL_ESTIMATE_TOTAL = None  # fill when official total is available


def fmt_inr(amount: float) -> str:
    """Format amount in Indian numbering (e.g. 1,84,50,000)."""
    val = round(float(amount), 2)
    sign = "-" if val < 0 else ""
    val = abs(val)
    whole, _, frac = f"{val:.2f}".partition(".")
    if len(whole) <= 3:
        grouped = whole
    else:
        last3 = whole[-3:]
        rest = whole[:-3]
        parts = []
        while rest:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        grouped = ",".join(parts + [last3])
    return f"{sign}Rs. {grouped}.{frac}"


def load_sor(path: str) -> list[dict]:
    with open(path, "rb") as f:
        parsed = parse_sor_pdf(f.read(), os.path.basename(path))
    return parsed.get("detailed_items", [])


def _is_valid_sor_match(item: dict, terms: list[str]) -> bool:
    desc = str(item.get("description", "")).lower()
    unit = str(item.get("unit", "")).lower()
    if unit != "cum":
        return False
    if any(skip in desc for skip in SOR_SKIP_KEYWORDS):
        return False
    return any(term in desc for term in terms)


def find_sor_rate(layer_name: str, rajpipla_items: list[dict], nh_items: list[dict]) -> tuple[float, str, str]:
    """Return (rate, source, item_code)."""
    terms = LAYER_SEARCH_TERMS.get(layer_name, [layer_name.lower()])
    for label, items in [("Rajpipla SOR", rajpipla_items), ("NH SOR", nh_items)]:
        for item in items:
            if not _is_valid_sor_match(item, terms):
                continue
            rate = float(item.get("rate_large_project", item.get("rate", 0)) or 0)
            if rate > 0:
                return rate, label, str(item.get("item_code", ""))
    return 0.0, "RATE_MISSING", ""


def calculate_quantities() -> list[dict]:
    rows: list[dict] = []
    for seg in TCS_DATA:
        tcs = seg["tcs_type"]
        length_m = float(seg["total_length_m"])
        width_m = float(seg["carriageway_width_m"]) * 2
        for layer in seg["layers"]:
            name = layer["name"]
            thick = float(layer["thickness_mm"])
            volume = round(length_m * width_m * (thick / 1000), 2)
            rows.append({
                "tcs_type": tcs,
                "layer": name,
                "description": LAYER_DESCRIPTIONS.get(name, name),
                "length_m": length_m,
                "width_m": width_m,
                "thickness_mm": thick,
                "volume_cum": volume,
            })
    return rows


def build_boq(quantity_rows: list[dict], rajpipla_items: list[dict], nh_items: list[dict]) -> tuple[list[dict], list[dict]]:
    boq_rows: list[dict] = []
    missing: list[dict] = []
    for row in quantity_rows:
        rate, source, item_code = find_sor_rate(row["layer"], rajpipla_items, nh_items)
        amount = round(row["volume_cum"] * rate, 2) if source != "RATE_MISSING" else 0.0
        entry = {
            "tcs_type": row["tcs_type"],
            "layer": row["layer"],
            "description": row["description"],
            "volume_cum": row["volume_cum"],
            "rate": rate,
            "amount": amount,
            "rate_source": source,
            "item_code": item_code,
        }
        boq_rows.append(entry)
        if source == "RATE_MISSING":
            missing.append(entry)
    return boq_rows, missing


def calculate_financials(road_work_total: float) -> dict[str, float]:
    contingency = round(road_work_total * 0.03, 2)
    labour_cess = round(road_work_total * 0.01, 2)
    subtotal = round(road_work_total + contingency + labour_cess, 2)
    gst = round(subtotal * 0.18, 2)
    grand_total = round(subtotal + gst, 2)
    return {
        "road_work_total": road_work_total,
        "contingency": contingency,
        "labour_cess": labour_cess,
        "subtotal": subtotal,
        "gst": gst,
        "grand_total": grand_total,
    }


def run_validation() -> str:
    lines: list[str] = []
    total_tcs_length = sum(seg["total_length_m"] for seg in TCS_DATA)

    lines.append(f"Project: {PROJECT_NAME}")
    lines.append(f"Chainage: {CHAINAGE}")
    lines.append(f"Total project length (TCS sum): {total_tcs_length:,}m (expected {TOTAL_PROJECT_LENGTH_M:,}m)")
    lines.append("")

    if not os.path.exists(RAJPIPLA_SOR):
        raise FileNotFoundError(f"Rajpipla SOR not found: {RAJPIPLA_SOR}")
    rajpipla_items = load_sor(RAJPIPLA_SOR)
    nh_items = load_sor(NH_SOR) if os.path.exists(NH_SOR) else []

    quantity_rows = calculate_quantities()

    lines.append("=" * 60)
    lines.append("ROAD WORK QUANTITIES")
    lines.append("=" * 60)
    lines.append(f"{'TCS':<6} {'Layer':<8} {'Length(m)':>10} {'Width(m)':>9} {'Thick(mm)':>10} {'Volume(cum)':>12}")
    lines.append(f"{'-' * 6} {'-' * 8} {'-' * 10} {'-' * 9} {'-' * 10} {'-' * 12}")
    total_volume = 0.0
    for row in quantity_rows:
        lines.append(
            f"{row['tcs_type']:<6} {row['layer']:<8} {row['length_m']:>10.0f} "
            f"{row['width_m']:>9.1f} {row['thickness_mm']:>10.0f} {row['volume_cum']:>12.2f}"
        )
        total_volume += row["volume_cum"]
    lines.append(f"{'':6} {'TOTAL':<8} {'':>10} {'':>9} {'':>10} {total_volume:>12.2f}")
    lines.append("")

    boq_rows, missing = build_boq(quantity_rows, rajpipla_items, nh_items)
    road_work_total = sum(r["amount"] for r in boq_rows)

    lines.append("=" * 60)
    lines.append("BOQ — ROAD WORK")
    lines.append("=" * 60)
    lines.append(
        f"{'Item':<6} {'Description':<24} {'Volume(cum)':>12} {'Rate(Rs)':>10} {'Amount(Rs)':>14}"
    )
    lines.append(f"{'-' * 6} {'-' * 24} {'-' * 12} {'-' * 10} {'-' * 14}")
    for idx, row in enumerate(boq_rows, 1):
        rate_str = f"{row['rate']:,.2f}" if row["rate_source"] != "RATE_MISSING" else "MISSING"
        desc = f"{row['tcs_type']} {row['description']}"[:24]
        lines.append(
            f"{idx:<6} {desc:<24} {row['volume_cum']:>12.2f} "
            f"{rate_str:>10} {row['amount']:>14,.2f}"
        )
    lines.append(f"{'':6} {'ROAD WORK TOTAL':<24} {'':>12} {'':>10} {road_work_total:>14,.2f}")

    if missing:
        lines.append("")
        lines.append("RATE_MISSING items:")
        for row in missing:
            lines.append(f"  - {row['tcs_type']} / {row['layer']} ({row['description']})")
    lines.append("")

    fin = calculate_financials(road_work_total)
    lines.append("=" * 60)
    lines.append("FINANCIAL SUMMARY")
    lines.append("=" * 60)
    lines.append(f"Road Work Total    : {fmt_inr(fin['road_work_total'])}")
    lines.append(f"Contingency (3%)   : {fmt_inr(fin['contingency'])}")
    lines.append(f"Labour Cess (1%)   : {fmt_inr(fin['labour_cess'])}")
    lines.append(f"Sub Total          : {fmt_inr(fin['subtotal'])}")
    lines.append(f"GST (18%)          : {fmt_inr(fin['gst'])}")
    lines.append(f"GRAND TOTAL        : {fmt_inr(fin['grand_total'])}")
    lines.append("")

    lines.append("=" * 60)
    lines.append("VALIDATION — COMPARISON WITH REAL ESTIMATE")
    lines.append("=" * 60)
    lines.append(f"Our System Total   : {fmt_inr(fin['grand_total'])}")
    if REAL_ESTIMATE_TOTAL is not None:
        diff_pct = ((fin["grand_total"] - REAL_ESTIMATE_TOTAL) / REAL_ESTIMATE_TOTAL) * 100
        lines.append(f"Real Estimate Total: {fmt_inr(REAL_ESTIMATE_TOTAL)}")
        lines.append(f"Difference         : {diff_pct:+.2f}%")
    else:
        lines.append("Real Estimate Total: Rs. (to be filled when available)")
        lines.append("Difference         : N/A")
    lines.append("Note: Structures not included in this validation run.")
    lines.append("      Real estimate includes structures — gap is expected.")
    lines.append("=" * 60)

    return "\n".join(lines) + "\n"


def test_validation_pipeline():
    output = run_validation()
    print(output)

    out_path = os.path.join(os.path.dirname(__file__), "VALIDATION_RESULTS.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)

    total_length = sum(seg["total_length_m"] for seg in TCS_DATA)
    assert total_length == TOTAL_PROJECT_LENGTH_M, f"Length mismatch: {total_length} vs {TOTAL_PROJECT_LENGTH_M}"

    quantity_rows = calculate_quantities()
    assert len(quantity_rows) == sum(len(seg["layers"]) for seg in TCS_DATA)
    assert all(row["volume_cum"] > 0 for row in quantity_rows)

    print(f"Saved: {out_path}")
    print("PASS: test_validation_pipeline")


if __name__ == "__main__":
    test_validation_pipeline()
