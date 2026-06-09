"""
Quantity calculation engine for civil engineering BOQ estimation.

Pure-Python volume/area formulas for road pavement layers and culvert structures.
Consumes drawing extraction dicts and returns itemised quantity sheets.
"""

from typing import Any


def earthwork_embankment(
    length_m: float,
    formation_width_m: float,
    avg_fill_depth_m: float,
    side_slope: float = 2.0,
) -> float:
    """Earthwork in embankment (cum)."""
    try:
        return round(
            (formation_width_m * avg_fill_depth_m + side_slope * avg_fill_depth_m ** 2) * length_m,
            2,
        )
    except (TypeError, ValueError):
        return 0.0


def gsb_volume(length_m: float, width_m: float, thickness_mm: float) -> float:
    """Granular sub-base volume (cum)."""
    return _layer_volume(length_m, width_m, thickness_mm)


def ctb_volume(length_m: float, width_m: float, thickness_mm: float) -> float:
    """Cement treated base volume (cum)."""
    return _layer_volume(length_m, width_m, thickness_mm)


def dbm_volume(length_m: float, width_m: float, thickness_mm: float) -> float:
    """Dense bituminous macadam volume (cum)."""
    return _layer_volume(length_m, width_m, thickness_mm)


def bc_volume(length_m: float, width_m: float, thickness_mm: float) -> float:
    """Bituminous concrete volume (cum)."""
    return _layer_volume(length_m, width_m, thickness_mm)


def tack_coat_area(length_m: float, width_m: float) -> float:
    """Tack coat area (sqm)."""
    try:
        return round(length_m * width_m, 2)
    except (TypeError, ValueError):
        return 0.0


def box_culvert_pcc_bed(
    span_m: float,
    cells: int,
    length_m: float,
    bed_thickness_m: float = 0.6,
) -> float:
    """PCC bed concrete for box culvert (cum)."""
    try:
        width = span_m * cells + 0.3 * (cells + 1)
        return round(width * bed_thickness_m * length_m, 2)
    except (TypeError, ValueError):
        return 0.0


def box_culvert_rcc_side_walls(
    height_m: float,
    length_m: float,
    cells: int,
    wall_thickness_m: float = 0.45,
) -> float:
    """RCC side walls for box culvert (cum)."""
    try:
        return round(wall_thickness_m * height_m * length_m * (cells + 1), 2)
    except (TypeError, ValueError):
        return 0.0


def box_culvert_rcc_base_slab(
    span_m: float,
    cells: int,
    length_m: float,
    slab_thickness_m: float = 0.5,
    wall_thickness_m: float = 0.45,
) -> float:
    """RCC base slab for box culvert (cum)."""
    try:
        width = span_m * cells + wall_thickness_m * (cells + 1)
        return round(width * slab_thickness_m * length_m, 2)
    except (TypeError, ValueError):
        return 0.0


def box_culvert_rcc_roof_slab(
    span_m: float,
    cells: int,
    length_m: float,
    slab_thickness_m: float = 0.5,
    wall_thickness_m: float = 0.45,
) -> float:
    """RCC roof slab for box culvert (cum)."""
    return box_culvert_rcc_base_slab(span_m, cells, length_m, slab_thickness_m, wall_thickness_m)


def box_culvert_reinforcement(
    total_rcc_volume: float,
    steel_ratio_kg_per_cum: float = 125.0,
) -> float:
    """Reinforcement steel for box culvert (MT)."""
    try:
        return round(total_rcc_volume * steel_ratio_kg_per_cum / 1000, 3)
    except (TypeError, ValueError):
        return 0.0


def box_culvert_formwork(
    height_m: float,
    span_m: float,
    cells: int,
    length_m: float,
) -> float:
    """Formwork area for box culvert (sqm)."""
    try:
        return round(2 * (height_m + span_m) * cells * length_m, 2)
    except (TypeError, ValueError):
        return 0.0


def pipe_culvert_pcc_bed(
    dia_mm: float,
    length_m: float,
    bed_thickness_m: float = 0.3,
) -> float:
    """PCC bed for pipe culvert (cum)."""
    try:
        width = dia_mm / 1000 + 0.6
        return round(width * bed_thickness_m * length_m, 2)
    except (TypeError, ValueError):
        return 0.0


def pipe_culvert_excavation(dia_mm: float, length_m: float) -> float:
    """Excavation for pipe culvert (cum)."""
    try:
        side = dia_mm / 1000 + 1.2
        return round(side * side * length_m, 2)
    except (TypeError, ValueError):
        return 0.0


def calculate_all_quantities(extraction: dict) -> dict[str, Any]:
    """
    Run all quantity formulas for road segments and structures in an extraction dict.

    Returns road_work and structures item lists with formula strings and quantities.
    """
    road_work: list[dict] = []
    structures: list[dict] = []

    try:
        segments = extraction.get("road_segments", [])
        for seg in segments:
            length_m = float(seg.get("length_km", 0)) * 1000
            width_m = float(seg.get("formation_width_m", seg.get("carriageway_width_m", 0)))
            chainage = f"{seg.get('chainage_start', '')} to {seg.get('chainage_end', '')}"

            ew_qty = earthwork_embankment(length_m, width_m, 1.2)
            road_work.append({
                "item_no": "RW-1",
                "description": f"Earthwork in embankment ({chainage})",
                "formula": f"{length_m} × {width_m} × 1.2 (with side slope)",
                "quantity": ew_qty,
                "unit": "cum",
            })

            for layer in seg.get("pavement_layers", []):
                name = str(layer.get("name", "")).upper()
                thick = float(layer.get("thickness_mm", 0))
                calc_map = {
                    "GSB": gsb_volume,
                    "CTB": ctb_volume,
                    "DBM": dbm_volume,
                    "BC": bc_volume,
                }
                calc_fn = calc_map.get(name)
                if not calc_fn:
                    continue
                qty = calc_fn(length_m, width_m, thick)
                road_work.append({
                    "item_no": f"RW-{name}",
                    "description": f"{name} layer ({chainage})",
                    "formula": f"{length_m} × {width_m} × {thick / 1000}",
                    "quantity": qty,
                    "unit": "cum",
                })

            tack = tack_coat_area(length_m, width_m)
            road_work.append({
                "item_no": "RW-TACK",
                "description": f"Tack coat ({chainage})",
                "formula": f"{length_m} × {width_m}",
                "quantity": tack,
                "unit": "sqm",
            })

        for idx, struct in enumerate(extraction.get("structures", []), 1):
            stype = str(struct.get("type", "")).lower()
            struct_id = struct.get("id", f"STR-{idx:03d}")
            chainage = struct.get("chainage", "")
            items: list[dict] = []

            if "box" in stype:
                span = float(struct.get("span_m", 0))
                height = float(struct.get("height_m", 0))
                length = float(struct.get("length_m", 0))
                cells = int(struct.get("cells", 1))

                pcc = box_culvert_pcc_bed(span, cells, length)
                walls = box_culvert_rcc_side_walls(height, length, cells)
                base = box_culvert_rcc_base_slab(span, cells, length)
                roof = box_culvert_rcc_roof_slab(span, cells, length)
                total_rcc = walls + base + roof
                steel = box_culvert_reinforcement(total_rcc)
                formwork = box_culvert_formwork(height, span, cells, length)

                items = [
                    {"item_no": "1.1", "description": "PCC M15 bed", "formula": f"({span}×{cells}+0.3×{cells+1})×0.6×{length}", "quantity": pcc, "unit": "cum"},
                    {"item_no": "1.2", "description": "RCC M35 side walls", "formula": f"0.45×{height}×{length}×{cells+1}", "quantity": walls, "unit": "cum"},
                    {"item_no": "1.3", "description": "RCC M35 base slab", "formula": f"({span}×{cells}+0.45×{cells+1})×0.5×{length}", "quantity": base, "unit": "cum"},
                    {"item_no": "1.4", "description": "RCC M35 roof slab", "formula": f"({span}×{cells}+0.45×{cells+1})×0.5×{length}", "quantity": roof, "unit": "cum"},
                    {"item_no": "1.5", "description": "Reinforcement steel", "formula": f"{total_rcc} × 125 / 1000", "quantity": steel, "unit": "MT"},
                    {"item_no": "1.6", "description": "Formwork", "formula": f"2×({height}+{span})×{cells}×{length}", "quantity": formwork, "unit": "sqm"},
                ]
            elif "pipe" in stype:
                dia = float(struct.get("dia_mm", struct.get("span_m", 0) * 1000))
                length = float(struct.get("length_m", 0))
                pcc = pipe_culvert_pcc_bed(dia, length)
                exc = pipe_culvert_excavation(dia, length)
                items = [
                    {"item_no": "1.1", "description": "PCC bed", "formula": f"({dia}/1000+0.6)×0.3×{length}", "quantity": pcc, "unit": "cum"},
                    {"item_no": "1.2", "description": "Excavation", "formula": f"({dia}/1000+1.2)²×{length}", "quantity": exc, "unit": "cum"},
                ]

            structures.append({
                "structure_id": struct_id,
                "chainage": chainage,
                "items": items,
            })

    except (TypeError, ValueError, KeyError) as exc:
        return {"road_work": road_work, "structures": structures, "error": str(exc)}

    return {"road_work": road_work, "structures": structures}


def calculate_quantities(estimation_type: str, extraction_data: dict) -> dict[str, Any]:
    """Router-compatible wrapper around calculate_all_quantities."""
    result = calculate_all_quantities(extraction_data)
    result["estimation_type"] = estimation_type
    return result


def _layer_volume(length_m: float, width_m: float, thickness_mm: float) -> float:
    try:
        return round(length_m * width_m * (thickness_mm / 1000), 2)
    except (TypeError, ValueError):
        return 0.0
