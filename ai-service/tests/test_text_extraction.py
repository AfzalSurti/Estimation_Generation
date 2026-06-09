import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from services.drawing_analyzer import extract_text_layer

TCS_PATH = "tests/pdfs/drawing/TCS.pdf"
PP_PATH  = "tests/pdfs/drawing/P&P.pdf"

def test_pdf(path, label):
    print(f"\n{'='*60}")
    print(f"FILE: {label}")
    print(f"{'='*60}")
    with open(path, "rb") as f:
        result = extract_text_layer(f.read())
    print(f"Total pages      : {result['total_pages']}")
    print(f"Pages with text  : {result['pages_with_text']}")
    print(f"\nPer-page word counts:")
    for p in result["pages"]:
        flag = "✓" if p["has_meaningful_text"] else "✗"
        print(f"  Page {p['page_num']:>2}: {p['word_count']:>4} words  {flag}")
    print(f"\nText from first 3 pages with content:")
    shown = 0
    for p in result["pages"]:
        if p["has_meaningful_text"] and shown < 3:
            print(f"\n--- Page {p['page_num']} ---")
            print(p["text"][:800])
            shown += 1

if __name__ == "__main__":
    test_pdf(TCS_PATH, "TCS.pdf (Typical Cross Section)")
    test_pdf(PP_PATH,  "P&P.pdf (Plan & Profile)")
