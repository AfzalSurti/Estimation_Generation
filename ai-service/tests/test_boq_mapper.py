import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv

load_dotenv()

from services.sor_parser import parse_sor_pdf
from services.boq_mapper import (
    search_sor_item,
    map_quantity_to_rate,
    apply_statutory_additions,
    generate_boq,
)

PDF_DIR = os.path.join(os.path.dirname(__file__), "pdfs")

if __name__ == "__main__":
    nh_path = os.path.join(PDF_DIR, "NH Division SOR.pdf")
    with open(nh_path, "rb") as f:
        sor_data = parse_sor_pdf(f.read(), os.path.basename(nh_path))

    sor_items = sor_data["detailed_items"]
    print(f"Loaded {len(sor_items)} NH SOR detailed items")

    match = search_sor_item("embankment construction", "cum", sor_items)
    print(f"search_sor_item match: {match['item_code'] if match else None} - {match['description'][:60] if match else 'None'}")

    qty_item = {
        "item_no": "RW-1",
        "description": "Construction of embankment with approved materials",
        "quantity": 1000.0,
        "unit": "cum",
    }
    mapped = map_quantity_to_rate(qty_item, sor_items, [])
    print(f"map_quantity_to_rate: source={mapped['rate_source']} rate={mapped['rate']} amount={mapped['amount']}")

    statutory = apply_statutory_additions(10_000_000)
    print(f"statutory grand_total: {statutory['grand_total']}")
    assert statutory["grand_total"] > 10_000_000

    boq = generate_boq(
        {"road_work": [qty_item], "structures": []},
        sor_items,
        [],
    )
    print(f"BOQ grand_total: {boq['grand_total']}")
    print("PASS: test_boq_mapper")
