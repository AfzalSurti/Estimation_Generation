import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.quantity_engine import (
    gsb_volume,
    box_culvert_pcc_bed,
    calculate_all_quantities,
)

MOCK_EXTRACTION = {
    "road_segments": [{
        "chainage_start": "00+000",
        "chainage_end": "44+000",
        "length_km": 44.0,
        "formation_width_m": 22.0,
        "carriageway_width_m": 7.0,
        "pavement_layers": [
            {"name": "GSB", "thickness_mm": 125},
            {"name": "CTB", "thickness_mm": 200},
            {"name": "DBM", "thickness_mm": 100},
            {"name": "BC", "thickness_mm": 50},
        ],
    }],
    "structures": [{
        "id": "BC-001",
        "type": "box_culvert",
        "chainage": "00+515",
        "cells": 1,
        "span_m": 3.0,
        "height_m": 2.0,
        "length_m": 25.5,
    }],
}

if __name__ == "__main__":
    gsb = gsb_volume(44000, 22.0, 125)
    print(f"gsb_volume: {gsb}")
    assert gsb == 121000.0, f"Expected 121000.0, got {gsb}"

    pcc = box_culvert_pcc_bed(3.0, 1, 25.5)
    print(f"box_culvert_pcc_bed: {pcc}")
    assert 54.0 < pcc < 56.0, f"Expected ~55.08, got {pcc}"

    quantities = calculate_all_quantities(MOCK_EXTRACTION)
    print(f"road_work items: {len(quantities['road_work'])}")
    print(f"structures: {len(quantities['structures'])}")
    for item in quantities["road_work"][:3]:
        print(f"  {item['description']}: {item['quantity']} {item['unit']}")
    print("PASS: test_quantity_engine")
