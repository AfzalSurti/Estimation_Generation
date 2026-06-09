import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv

load_dotenv()

from services.drawing_analyzer import (
    rasterize_pdf_pages,
    classify_page,
    extract_from_page,
    merge_extractions,
)

from tests.paths import TCS_DRAWING, PLAN_PROFILE_DRAWING

if __name__ == "__main__":
    pdf_path = TCS_DRAWING if os.path.exists(TCS_DRAWING) else PLAN_PROFILE_DRAWING
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    pages = rasterize_pdf_pages(file_bytes)
    print(f"rasterized pages: {len(pages)}")
    assert len(pages) > 0, "rasterize_pdf_pages returned no pages"

    first = pages[0]
    print(f"page 1 size: {first['width']}x{first['height']}, base64 len: {len(first['base64'])}")

    use_mock = os.getenv("DRAWING_TEST_MOCK", "true").lower() == "true"
    classification = classify_page(first["base64"], 1, mock=use_mock)
    print(f"classification: {classification}")

    extraction = extract_from_page(first["base64"], classification.get("type", "title_sheet"), mock=use_mock)
    print(f"extraction keys: {list(extraction.keys())}")

    merged = merge_extractions([{**extraction, "page_type": classification.get("type", "title_sheet")}])
    print(f"merged drawing_type: {merged['drawing_type']}")
    print(f"merged confidence: {merged['extraction_confidence']}")
    print("PASS: test_drawing_analyzer")
