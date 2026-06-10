import os
import re
import sys

import pdfplumber

ESTIMATE_DIR = os.path.join(os.path.dirname(__file__), "pdfs", "estimate")

PDF_PATHS = [
    os.path.join(ESTIMATE_DIR, "Ankleshwar-Rajpipla HSC - Bharuch Estimate - R3.pdf"),
    os.path.join(
        ESTIMATE_DIR,
        "Ankleshwar-Rajpipla HSC - Bharuch Estimate - R3 (New Retaining Wall).pdf",
    ),
]

FINANCIAL_KEYWORDS = [
    "RECAPITULATION",
    "RECAP",
    "ABSTRACT",
    "ROAD WORK",
    "GRAND TOTAL",
    "TOTAL COST",
    "STRUCTURE",
    "CULVERT",
    "SUMMARY",
    "CONTINGENC",
    "LABOUR CESS",
    "GST",
]


def extract_estimate_values(path: str) -> dict:
    results = {
        "path": path,
        "exists": os.path.exists(path),
        "pages_found": [],
        "page_texts": {},
        "recapitulation": {},
        "abstract_items": [],
        "grand_total": None,
        "road_work_total": None,
        "structures_total": None,
        "all_amounts_found": [],
    }

    if not results["exists"]:
        print(f"\nFILE NOT FOUND: {path}")
        return results

    with pdfplumber.open(path) as pdf:
        print(f"\n{'#' * 60}")
        print(f"FILE: {os.path.basename(path)}")
        print(f"Total pages: {len(pdf.pages)}")

        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            text_upper = text.upper()

            if any(kw in text_upper for kw in FINANCIAL_KEYWORDS):
                print(f"\n{'=' * 60}")
                print(f"PAGE {i} — financial content found")
                print(f"{'=' * 60}")
                print(text[:2000])
                results["pages_found"].append(i)
                results["page_texts"][i] = text[:2000]

            amounts = re.findall(r"[\d,]{6,}\.?\d*", text)
            for amt in amounts:
                try:
                    val = float(amt.replace(",", ""))
                    if val > 100000:
                        results["all_amounts_found"].append({
                            "page": i,
                            "value": val,
                            "raw": amt,
                        })
                except ValueError:
                    pass

    return results


def print_summary(result: dict) -> None:
    print(f"\nPages with financial content: {result['pages_found']}")
    print(f"Total large amounts found: {len(result['all_amounts_found'])}")
    print("\nTop 20 largest amounts across all pages:")
    sorted_amounts = sorted(
        result["all_amounts_found"],
        key=lambda x: x["value"],
        reverse=True,
    )
    for amt in sorted_amounts[:20]:
        print(f"  Page {amt['page']:>3}: Rs. {amt['value']:>20,.2f}  (raw: {amt['raw']})")


def search_rajpipla_sor() -> None:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from services.sor_parser import parse_sor_pdf

    sor_path = os.path.join(os.path.dirname(__file__), "pdfs", "sor", "Rajpipla SOR.pdf")
    print(f"\n{'#' * 60}")
    print("RAJPIPLA SOR — DBM/GSB/ROAD ITEM SEARCH")
    print(f"{'#' * 60}")

    if not os.path.exists(sor_path):
        print(f"SOR NOT FOUND: {sor_path}")
        return

    with open(sor_path, "rb") as f:
        result = parse_sor_pdf(f.read(), "Rajpipla SOR.pdf")

    items = result["detailed_items"]
    keywords = [
        "bituminous",
        "macadam",
        "granular",
        "sub",
        "gsb",
        "dbm",
        "dense",
        "base",
        "concrete",
        "pavement",
        "asphalt",
        "bm ",
        "premix",
        "wearing",
        "carpet",
    ]

    print("MATCHING ITEMS IN RAJPIPLA SOR:")
    print(f"{'Code':<10} {'Unit':<8} {'Rate':<12} {'Description':<60}")
    print("-" * 90)
    for item in items:
        desc = item["description"].lower()
        if any(k in desc for k in keywords):
            print(
                f"{item['item_code']:<10} {item['unit']:<8} "
                f"Rs.{item['rate_large_project']:<10} {item['description'][:60]}"
            )


if __name__ == "__main__":
    all_results = []
    for pdf_path in PDF_PATHS:
        result = extract_estimate_values(pdf_path)
        all_results.append(result)
        if result["exists"]:
            print_summary(result)

    search_rajpipla_sor()
