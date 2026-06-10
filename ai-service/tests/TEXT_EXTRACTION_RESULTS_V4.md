
============================================================
TEST: TCS Extraction
============================================================
Road segments found: 9

  TCS-1
    formation_width_m : 21.5
    carriageway_width_m: 7.0
    layers            : [{'name': 'BC', 'thickness_mm': 40}, {'name': 'DBM', 'thickness_mm': 50}]
    chainage_ranges   : 6 ranges
    total_length_m    : 9671
    ranges[0]       : 43+816 to 44+188 = 372m
    ranges[1]       : 45+716 to 51+300 = 5584m
    confidence        : 1.0

  TCS-2
    formation_width_m : 21.5
    carriageway_width_m: 7.0
    layers            : [{'name': 'BC', 'thickness_mm': 40}, {'name': 'DBM', 'thickness_mm': 50}]
    chainage_ranges   : 1 ranges
    total_length_m    : 600
    ranges[0]       : 51+300 to 51+900 = 600m
    confidence        : 1.0

  TCS-3
    formation_width_m : None
    carriageway_width_m: 7.0
    layers            : [{'name': 'PQC', 'thickness_mm': 300}, {'name': 'CTB', 'thickness_mm': 300}]
    chainage_ranges   : 1 ranges
    total_length_m    : 500
    ranges[0]       : 52+300 to 52+800 = 500m
    confidence        : 0.9

  TCS-4
    formation_width_m : 21.5
    carriageway_width_m: 7.0
    layers            : [{'name': 'BC', 'thickness_mm': 40}, {'name': 'DBM', 'thickness_mm': 50}]
    chainage_ranges   : 1 ranges
    total_length_m    : 400
    ranges[0]       : 51+900 to 52+300 = 400m
    confidence        : 1.0

  TCS-5
    formation_width_m : 1.0
    carriageway_width_m: 7.0
    layers            : [{'name': 'BC', 'thickness_mm': 40}, {'name': 'DBM', 'thickness_mm': 50}]
    chainage_ranges   : 1 ranges
    total_length_m    : 310
    ranges[0]       : 54+390 to 54+700 = 310m
    confidence        : 1.0

  TCS-6
    formation_width_m : 21.5
    carriageway_width_m: 7.0
    layers            : [{'name': 'BC', 'thickness_mm': 40}, {'name': 'DBM', 'thickness_mm': 120}, {'name': 'GSB', 'thickness_mm': 125}]
    chainage_ranges   : 1 ranges
    total_length_m    : 630
    ranges[0]       : 60+570 to 61+200 = 630m
    confidence        : 1.0

  TCS-1A
    formation_width_m : 21.0
    carriageway_width_m: 7.0
    layers            : [{'name': 'BC', 'thickness_mm': 40}, {'name': 'DBM', 'thickness_mm': 50}]
    chainage_ranges   : 6 ranges
    total_length_m    : 4884
    ranges[0]       : 44+188 to 44+816 = 628m
    ranges[1]       : 45+146 to 45+716 = 570m
    confidence        : 1.0

  TCS-2A
    formation_width_m : 21.0
    carriageway_width_m: 7.0
    layers            : [{'name': 'BC', 'thickness_mm': 40}, {'name': 'DBM', 'thickness_mm': 50}]
    chainage_ranges   : 2 ranges
    total_length_m    : 555
    ranges[0]       : 44+816 to 45+146 = 330m
    ranges[1]       : 54+165 to 54+390 = 225m
    confidence        : 1.0

  TCS-4A
    formation_width_m : 21.0
    carriageway_width_m: 7.0
    layers            : [{'name': 'BC', 'thickness_mm': 40}, {'name': 'DBM', 'thickness_mm': 50}]
    chainage_ranges   : 2 ranges
    total_length_m    : 900
    ranges[0]       : 57+215 to 57+715 = 500m
    ranges[1]       : 59+300 to 59+700 = 400m
    confidence        : 1.0

  PROJECT TOTAL LENGTH: 18450m

PASS: test_tcs_extraction

============================================================
TEST: P&P Extraction
============================================================
Structures found: 49

  PC-001 @ 44+615
    type       : pipe_culvert
    size       : 1X0.9m PIPE CULVERT
    action     : RETAIN
    confidence : 0.85
    dia_m      : 0.9

  BC-001 @ 45+160
    type       : box_culvert
    size       : 2X7.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 7.0 height_m: None

  BC-002 @ 45+580
    type       : box_culvert
    size       : 1X2.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 2.0 height_m: None

  PC-002 @ 46+140
    type       : pipe_culvert
    size       : 1X1.2m ├ÿ HPC
    action     : RETAIN
    confidence : 0.9
    dia_m      : 1.2

  BC-003 @ 46+620
    type       : box_culvert
    size       : 2X3.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 3.0 height_m: None

  PC-003 @ 46+910
    type       : pipe_culvert
    size       : 2X1.2m ├ÿ HPC
    action     : RETAIN
    confidence : 0.9
    dia_m      : 1.2

  BC-004 @ 47+010
    type       : box_culvert
    size       : 1X2.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 2.0 height_m: None

  MB-001 @ 47+660
    type       : minor_bridge
    size       : 4X5.0m MNB
    action     : RETAIN
    confidence : 0.9
    span_m     : 5.0 height_m: None

  MB-002 @ 48+160
    type       : minor_bridge
    size       : 2X7.5m MNB
    action     : RETAIN
    confidence : 0.9
    span_m     : 7.5 height_m: None

  BC-005 @ 48+830
    type       : box_culvert
    size       : 1X6.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 6.0 height_m: None

  BC-006 @ 49+125
    type       : box_culvert
    size       : 1X4.5m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 4.5 height_m: None

  CS-001 @ 49+290
    type       : canal_syphon
    size       : 1X8.0m CANAL SYPHON
    action     : RETAIN
    confidence : 0.9
    span_m     : 8.0 height_m: None

  MB-003 @ 49+390
    type       : minor_bridge
    size       : 6X4.8m MNB
    action     : RETAIN
    confidence : 0.9
    span_m     : 4.8 height_m: None

  MB-004 @ 49+720
    type       : minor_bridge
    size       : MNB
    action     : RETAIN
    confidence : 0.9

  BC-007 @ 50+210
    type       : box_culvert
    size       : 6X4.8m ├ÿ HPC
    action     : RETAIN
    confidence : 0.9
    span_m     : 4.8 height_m: None

  BC-008 @ 50+375
    type       : box_culvert
    size       : 6X4.8m ├ÿ BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 4.8 height_m: None

  BC-009 @ 50+530
    type       : box_culvert
    size       : 1X2.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 2.0 height_m: None

  BC-010 @ 50+918
    type       : box_culvert
    size       : 1X2.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 2.0 height_m: None

  BC-011 @ 51+038
    type       : box_culvert
    size       : 1X5.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 5.0 height_m: None

  BC-012 @ 51+250
    type       : box_culvert
    size       : 1X2.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 2.0 height_m: None

  MJ-001 @ 51+300
    type       : major_bridge
    size       : 2X7.2m CANAL BRIDGE
    action     : RETAIN
    confidence : 0.9
    span_m     : 7.2 height_m: None

  BC-013 @ 51+405
    type       : box_culvert
    size       : 1X3.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 3.0 height_m: None

  BC-014 @ 51+535
    type       : box_culvert
    size       : 1X8.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 8.0 height_m: None

  PC-004 @ 51+740
    type       : pipe_culvert
    size       : 1X0.9m ├ÿ HPC
    action     : RETAIN
    confidence : 0.9
    dia_m      : 0.9

  BC-015 @ 51+950
    type       : box_culvert
    size       : 1X0.9m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 0.9 height_m: None

  ST-001 @ 52+590
    type       : unknown
    size       : UNKNOWN
    action     : RETAIN
    confidence : 0.7

  BC-016 @ 52+810
    type       : box_culvert
    size       : 1X2.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.85
    span_m     : 2.0 height_m: None

  MJ-002 @ 52+840
    type       : major_bridge
    size       : 1X15.3m Canal Bridge
    action     : RETAIN
    confidence : 0.7
    span_m     : 15.3 height_m: None

  MB-005 @ 53+095
    type       : minor_bridge
    size       : 2X7.5m MNB
    action     : RETAIN
    confidence : 0.9
    span_m     : 7.5 height_m: None

  BC-017 @ 53+565
    type       : box_culvert
    size       : 1X2.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 2.0 height_m: None

  BC-018 @ 53+715
    type       : box_culvert
    size       : 1X3.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 3.0 height_m: None

  CS-002 @ 53+820
    type       : canal_syphon
    size       : 1X3.0m CANAL SYPHON
    action     : RETAIN
    confidence : 0.9
    span_m     : 3.0 height_m: None

  ST-002 @ 54+390
    type       : unknown
    size       : UNKNOWN
    action     : RETAIN
    confidence : 0.7

  ST-003 @ 55+068
    type       : unknown
    size       : UNKNOWN
    action     : RETAIN
    confidence : 0.7

  BC-019 @ 55+420
    type       : box_culvert
    size       : 1X3.5m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 3.5 height_m: None

  BC-020 @ 55+830
    type       : box_culvert
    size       : 1X4.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 4.0 height_m: None

  BC-021 @ 56+110
    type       : box_culvert
    size       : 1X2.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 2.0 height_m: None

  BC-022 @ 56+275
    type       : box_culvert
    size       : 1X3.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 3.0 height_m: None

  BC-023 @ 56+500
    type       : box_culvert
    size       : 1X2.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 2.0 height_m: None

  MB-006 @ 56+645
    type       : minor_bridge
    size       : 3X7m MNB
    action     : RETAIN
    confidence : 0.9
    span_m     : 7.0 height_m: None

  BC-024 @ 57+270
    type       : box_culvert
    size       : 1X2.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 2.0 height_m: None

  BC-025 @ 57+665
    type       : box_culvert
    size       : 1X5.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 5.0 height_m: None

  BC-026 @ 58+030
    type       : box_culvert
    size       : 1X2.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 2.0 height_m: None

  BC-027 @ 58+440
    type       : box_culvert
    size       : 1X2.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 2.0 height_m: None

  BC-028 @ 58+670
    type       : box_culvert
    size       : 1X2.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 2.0 height_m: None

  BC-029 @ 59+600
    type       : box_culvert
    size       : 1X2.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 2.0 height_m: None

  BC-030 @ 60+480
    type       : box_culvert
    size       : 1X4.0m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 4.0 height_m: None

  MB-007 @ 61+700
    type       : minor_bridge
    size       : 8X21.55m MNB
    action     : RETAIN
    confidence : 0.9
    span_m     : 21.55 height_m: None

  BC-031 @ 62+060
    type       : box_culvert
    size       : 2X0.9m BOX CULVERT
    action     : RETAIN
    confidence : 0.9
    span_m     : 0.9 height_m: None

PASS: test_pp_extraction

============================================================
TEST: Full Pipeline (TCS + P&P)
============================================================
Summary: 9 road segments, 49 structures
Extraction confidence: 0.9
TCS pages parsed: 9
P&P pages parsed: 19

PASS: test_full_pipeline

============================================================
ALL DRAWING ANALYZER TESTS PASSED
============================================================
