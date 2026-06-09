import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.rate_analysis_engine import (
    calculate_lead_carriage,
    create_ra_item,
    get_ra_summary,
)

if __name__ == "__main__":
    rate_at_site = calculate_lead_carriage(
        base_rate=503.50,
        lead_km=179,
        carriage_rate_per_km=2.42,
        first_5km_rate=101.40,
    )
    print(f"rate_at_site (179km lead): {rate_at_site}")
    assert rate_at_site == 1431.58, f"Expected 1431.58, got {rate_at_site}"

    ingredients = [
        {
            "sor_code": "M-081",
            "description": "Cement",
            "quantity": 150.0,
            "unit": "kg",
            "base_rate": 5234.0,
            "base_unit": "tonne",
            "conversion_factor": 0.001,
            "lead_km": 0,
            "carriage_rate_per_km": 0,
            "first_5km_rate": 0,
        },
        {
            "sor_code": "M-045",
            "description": "Coarse aggregate 20mm",
            "quantity": 1.35,
            "unit": "cum",
            "base_rate": 850.0,
            "base_unit": "cum",
            "conversion_factor": 1.0,
            "lead_km": 179,
            "carriage_rate_per_km": 2.42,
            "first_5km_rate": 101.40,
        },
        {
            "sor_code": "L-10",
            "description": "Mason",
            "quantity": 0.5,
            "unit": "day",
            "base_rate": 633.0,
            "base_unit": "day",
            "conversion_factor": 1.0,
            "lead_km": 0,
            "carriage_rate_per_km": 0,
            "first_5km_rate": 0,
        },
    ]

    ra_item = create_ra_item(
        item_id="RA-001",
        description="Cement Treated Base (CTB) 200mm",
        unit="cum",
        ingredients=ingredients,
        overhead_percent=10.0,
        sor_reference="R&B Bharuch 2024-25",
    )

    print(f"subtotal: {ra_item['subtotal']}")
    print(f"overhead: {ra_item['overhead_amount']}")
    print(f"final_rate: {ra_item['final_rate']}")

    summary = get_ra_summary([ra_item])
    print(f"summary: {summary}")
    print("PASS: test_rate_analysis")
