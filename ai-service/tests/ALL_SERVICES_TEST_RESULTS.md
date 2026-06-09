## Test Run Date

2026-06-09

## Service 1: rate_analysis_engine.py — PASS

| Test | Result |
|------|--------|
| `calculate_lead_carriage(503.50, 179km, 2.42, 101.40)` | rate_at_site = **1431.58** |
| `create_ra_item` CTB with 3 ingredients | subtotal = 3502.01, overhead = 350.20, **final_rate = 3852.21** |
| `get_ra_summary` | 1 item returned |

## Service 2: drawing_analyzer.py — PASS

| Test | Result |
|------|--------|
| `rasterize_pdf_pages` (NH Division SOR.pdf) | **91 pages** rasterized via PyMuPDF |
| Page 1 size | 1241×1754, base64 length 183140 |
| `classify_page` (mock mode) | type=title_sheet, confidence=0.85 |
| `extract_from_page` (mock mode) | extraction keys returned |
| `merge_extractions` | drawing_type=general_notes, confidence=0.8 |

> Vision AI calls use mock mode in tests (`DRAWING_TEST_MOCK=true` default) to avoid API quota limits. Live vision calls use `VISION_MODEL` from `.env`.

## Service 3: quantity_engine.py — PASS

| Test | Expected | Actual |
|------|----------|--------|
| `gsb_volume(44000, 22.0, 125)` | 121000.0 | **121000.0** ✓ |
| `box_culvert_pcc_bed(3.0, 1, 25.5)` | ~55.08 | **55.08** ✓ |
| `calculate_all_quantities` mock extraction | road + structure items | **6 road_work + 1 structure** |

Sample road_work quantities:
- Earthwork embankment: 1,288,320 cum
- GSB layer: 121,000 cum
- CTB layer: 193,600 cum

## Service 4: boq_mapper.py — PASS

| Test | Result |
|------|--------|
| NH SOR items loaded | **221** detailed items |
| `search_sor_item("embankment construction", "cum")` | matched **3.16** |
| `map_quantity_to_rate` (1000 cum) | source=SOR, rate=47.6, amount=47,600 |
| `apply_statutory_additions(10,000,000)` | grand_total = **12,254,000** |
| `generate_boq` | grand_total = 47,600 |

## Status: ALL PASS

All 4 services implemented and all 4 test suites passing.

### Files created

- `services/rate_analysis_engine.py`
- `services/drawing_analyzer.py`
- `services/quantity_engine.py`
- `services/boq_mapper.py`
- `services/requirements.txt`
- `tests/test_rate_analysis.py`
- `tests/test_drawing_analyzer.py`
- `tests/test_quantity_engine.py`
- `tests/test_boq_mapper.py`
