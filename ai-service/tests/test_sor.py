import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.sor_parser import parse_sor_pdf
from tests.paths import RAJPIPLA_SOR, NH_SOR

RB_SOR_PATH = RAJPIPLA_SOR
NH_SOR_PATH = NH_SOR

def test_sor(path: str, label: str):
    print(f"\n{'='*50}")
    print(f"Testing: {label}")
    print(f"{'='*50}")

    if not os.path.exists(path):
        print(f"FILE NOT FOUND: {path}")
        return

    with open(path, "rb") as f:
        result = parse_sor_pdf(f.read(), os.path.basename(path))

    print(f"SOR Type        : {result['sor_type']}")
    print(f"Total Pages     : {result['total_pages']}")
    print(f"Base Inputs     : {result['base_inputs_found']}")
    print(f"Detailed Items  : {result['detailed_items_found']}")
    print(f"Failed Pages    : {len(result['failed_pages'])}")

    if result['base_inputs']:
        print("\nSample Base Inputs (first 3):")
        for item in result['base_inputs'][:3]:
            print(f"  {item['code']:<12} {item['unit']:<8} Rs.{item['rate']:<10} {item['description'][:50]}")

    if result['detailed_items']:
        print("\nSample Detailed Items (first 3):")
        for item in result['detailed_items'][:3]:
            print(f"  {item['item_code']:<10} {item['unit']:<8} Rs.{item['rate_large_project']:<10} {item['description'][:50]}")

    if result['failed_pages']:
        print(f"\nFailed pages: {[p['page'] for p in result['failed_pages']]}")

if __name__ == "__main__":
    test_sor(RB_SOR_PATH, "Rajpipla SOR")
    test_sor(NH_SOR_PATH, "NH Division SOR")