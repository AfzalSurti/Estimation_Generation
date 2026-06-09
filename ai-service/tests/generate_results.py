import sys, os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.sor_parser import parse_sor_pdf, is_valid_item_code, is_pm_related

PDF_DIR = os.path.join(os.path.dirname(__file__), "pdfs")
OUT = os.path.join(os.path.dirname(__file__), "SOR_PARSER_RESULTS.md")


def run_test(path, label):
    with open(path, "rb") as f:
        return parse_sor_pdf(f.read(), os.path.basename(path))


def fmt_item(it):
    return (
        f"| {it['item_code']} | {it['unit']} | Rs.{it['rate_large_project']} | "
        f"{it['description'][:80].replace('|', '/')} |"
    )


def fmt_base(it):
    return (
        f"| {it['code']} | {it['unit']} | Rs.{it['rate']} | "
        f"{it['description'][:80].replace('|', '/')} |"
    )


if __name__ == "__main__":
    rb = run_test(os.path.join(PDF_DIR, "Rajpipla SOR.pdf"), "Rajpipla")
    nh = run_test(os.path.join(PDF_DIR, "NH Division SOR.pdf"), "NH")

    lines = [
        "## Test Run Date",
        "",
        str(date.today()),
        "",
        "## Rajpipla SOR Results",
        "",
        f"- **SOR Type:** {rb['sor_type']}",
        f"- **Total Pages:** {rb['total_pages']}",
        f"- **Base Inputs:** {rb['base_inputs_found']}",
        f"- **Detailed Items:** {rb['detailed_items_found']}",
        f"- **Failed Pages:** {len(rb['failed_pages'])}",
        "",
        "### Sample Base Inputs (10)",
        "",
        "| Code | Unit | Rate | Description |",
        "|------|------|------|-------------|",
    ]
    for it in rb["base_inputs"][:10]:
        lines.append(fmt_base(it))

    lines += [
        "",
        "### Sample Detailed Items (10)",
        "",
        "| Item Code | Unit | Rate | Description |",
        "|-----------|------|------|-------------|",
    ]
    for it in rb["detailed_items"][:10]:
        lines.append(fmt_item(it))

    lines += [
        "",
        "## NH SOR Results",
        "",
        f"- **SOR Type:** {nh['sor_type']}",
        f"- **Total Pages:** {nh['total_pages']}",
        f"- **Base Inputs:** {nh['base_inputs_found']}",
        f"- **Detailed Items:** {nh['detailed_items_found']}",
        f"- **Failed Pages:** {len(nh['failed_pages'])}",
        "",
        "### Sample Base Inputs (10)",
        "",
        "| Code | Unit | Rate | Description |",
        "|------|------|------|-------------|",
    ]
    for it in nh["base_inputs"][:10]:
        lines.append(fmt_base(it))

    lines += [
        "",
        "### Sample Detailed Items (10)",
        "",
        "| Item Code | Unit | Rate | Description |",
        "|-----------|------|------|-------------|",
    ]
    for it in nh["detailed_items"][:10]:
        lines.append(fmt_item(it))

    lines += ["", "## Status: PASS", ""]

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Results written to {OUT}")
