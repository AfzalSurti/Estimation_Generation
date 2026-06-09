"""Shared PDF paths for tests."""
import os

PDF_DIR = os.path.join(os.path.dirname(__file__), "pdfs")
SOR_DIR = os.path.join(PDF_DIR, "sor")
DRAWING_DIR = os.path.join(PDF_DIR, "drawing")

RAJPIPLA_SOR = os.path.join(SOR_DIR, "Rajpipla SOR.pdf")
NH_SOR = os.path.join(SOR_DIR, "NH Division SOR.pdf")
TCS_DRAWING = os.path.join(DRAWING_DIR, "TCS.pdf")
PLAN_PROFILE_DRAWING = os.path.join(DRAWING_DIR, "P&P.pdf")
