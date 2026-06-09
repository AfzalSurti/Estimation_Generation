## Test Run Date

2026-06-09

## Folder Structure

```
tests/pdfs/
  sor/
    NH Division SOR.pdf
    Rajpipla SOR.pdf
  drawing/
    TCS.pdf          (Typical Cross Section, 10 pages)
    P&P.pdf          (Plan & Profile, 20 pages)
```

## Pipeline Steps

| Step | Service | Result |
|------|---------|--------|
| 1. SOR Parse | sor_parser.py | NH_SOR, 300 base inputs, 221 detailed items |
| 2. Drawing AI | drawing_analyzer.py | TCS: 1 road segment; P&P: 0 segments (low AI confidence) |
| 3. Quantities | quantity_engine.py | 6 road work items |
| 4. BOQ Map | boq_mapper.py | 6/6 items mapped to SOR rates |
| 5. Statutory | boq_mapper.py | Contingency + labour cess + GST applied |

## Estimation Output

| Item | Value |
|------|-------|
| Road work BOQ total | Rs. 694,852,576.00 |
| Structures total | Rs. 0.00 |
| Contingency (3%) | Rs. 20,845,577.28 |
| Labour cess (1%) | Rs. 6,948,525.76 |
| GST (18%) | Rs. 128,825,667.59 |
| **FINAL ESTIMATE** | **Rs. 851,472,346.63** |

## Sample BOQ Line Items

- Earthwork in embankment: 1,288,320 cum
- GSB layer: 242,000 cum
- CTB layer: 193,600 cum
- DBM layer: 96,800 cum
- BC layer: 48,400 cum
- Tack coat: 968,000 sqm

## Status: PASS (pipeline works end-to-end)

## Notes for Engineer Review

- Vision AI confidence was **low (0.1)** on TCS drawing — quantities use AI-extracted 44 km length × 22 m width
- P&P drawing returned no segments — structures/culverts not yet extracted
- Amounts are **structurally correct** but should be validated against actual drawing dimensions before use in a real DPR
- Run: `python tests/test_estimation_pipeline.py` (set `DRAWING_TEST_MOCK=true` to skip live AI)
