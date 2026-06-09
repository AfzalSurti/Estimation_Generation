"""
Drawing analyzer for civil engineering BOQ estimation.

Rasterizes engineering drawing PDFs and uses OpenRouter vision models to classify
pages and extract road segments, pavement layers, and structure details.
"""

import base64
import io
import json
import os
import re
from typing import Any, Optional

from openai import OpenAI

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def _get_client() -> OpenAI:
    """Create OpenRouter OpenAI-compatible client."""
    return OpenAI(
        api_key=os.getenv("API_KEY"),
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )


def _get_vision_model() -> str:
    return os.getenv("VISION_MODEL", "nvidia/nemotron-nano-12b-v2-vl:free")


def _parse_json_response(text: str) -> dict:
    """Extract JSON object from model response text."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def _image_to_base64(image: "Image.Image") -> str:
    """Convert PIL Image to JPEG base64 string."""
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def rasterize_pdf_pages(file_bytes: bytes) -> list[dict]:
    """
    Convert each PDF page to a base64-encoded JPEG image.

    Returns list of dicts with page_num, base64, width, height.
    """
    pages: list[dict] = []

    if PDF2IMAGE_AVAILABLE and PIL_AVAILABLE:
        try:
            images = convert_from_bytes(file_bytes, dpi=150)
            for i, image in enumerate(images, 1):
                pages.append({
                    "page_num": i,
                    "base64": _image_to_base64(image),
                    "width": image.width,
                    "height": image.height,
                })
            if pages:
                return pages
        except Exception:
            pass

    if PYMUPDF_AVAILABLE and PIL_AVAILABLE:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for i, page in enumerate(doc, 1):
                pix = page.get_pixmap(dpi=150)
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                pages.append({
                    "page_num": i,
                    "base64": _image_to_base64(image),
                    "width": image.width,
                    "height": image.height,
                })
            doc.close()
        except Exception:
            return pages

    return pages


def _call_vision_ai(page_base64: str, prompt: str) -> str:
    """Send image + prompt to OpenRouter vision model."""
    client = _get_client()
    response = client.chat.completions.create(
        model=_get_vision_model(),
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{page_base64}"}},
                {"type": "text", "text": prompt},
            ],
        }],
        max_tokens=1024,
    )
    return response.choices[0].message.content or ""


def classify_page(page_base64: str, page_num: int, mock: bool = False) -> dict:
    """
    Classify an engineering drawing page using vision AI.

    Returns page type, confidence, and feature flags.
    """
    default = {
        "page_num": page_num,
        "type": "general_notes",
        "confidence": 0.0,
        "contains_chainages": False,
        "structure_types_visible": [],
        "notes": "",
    }

    if mock:
        return {
            **default,
            "type": "title_sheet",
            "confidence": 0.85,
            "notes": "Mock classification for testing",
        }

    prompt = (
        "Classify this engineering drawing page. Return JSON only:\n"
        "{\n"
        "  'type': 'plan_view|profile_view|typical_cross_section|"
        "structure_drawing|general_notes|title_sheet|legend',\n"
        "  'confidence': 0.0-1.0,\n"
        "  'contains_chainages': true/false,\n"
        "  'structure_types_visible': [],\n"
        "  'notes': 'brief description'\n"
        "}"
    )

    try:
        raw = _call_vision_ai(page_base64, prompt)
        parsed = _parse_json_response(raw)
        if not parsed:
            return default
        return {
            "page_num": page_num,
            "type": parsed.get("type", "general_notes"),
            "confidence": float(parsed.get("confidence", 0.5)),
            "contains_chainages": bool(parsed.get("contains_chainages", False)),
            "structure_types_visible": parsed.get("structure_types_visible", []),
            "notes": parsed.get("notes", ""),
        }
    except Exception as exc:
        return {**default, "notes": f"classification failed: {exc}"}


def extract_from_page(page_base64: str, page_type: str, mock: bool = False) -> dict:
    """
    Extract structured data from a drawing page based on its classified type.

    Uses type-specific prompts for plan views, cross sections, and structures.
    """
    if mock:
        if page_type == "typical_cross_section":
            return {
                "formation_width_m": 21.5,
                "carriageway_width_m": 7.0,
                "layers": [
                    {"name": "GSB", "thickness_mm": 250},
                    {"name": "CTB", "thickness_mm": 200},
                ],
                "confidence": 0.9,
            }
        if page_type == "plan_view":
            return {
                "chainages": ["00+000", "44+000"],
                "structures": [{"chainage": "00+515", "type": "box_culvert", "annotation": "1x3x2", "confidence": 0.9}],
            }
        return {"confidence": 0.8}

    prompts = {
        "plan_view": (
            "Extract from this road plan view drawing. Return JSON only:\n"
            "{\n"
            "  'chainages': ['00+000', '01+000'],\n"
            "  'structures': [\n"
            "    {'chainage': '00+515', 'type': 'box_culvert',\n"
            "     'annotation': '1x3x2', 'confidence': 0.9}\n"
            "  ]\n"
            "}"
        ),
        "typical_cross_section": (
            "Extract pavement layers from this cross section. Return JSON only:\n"
            "{\n"
            "  'formation_width_m': 21.5,\n"
            "  'carriageway_width_m': 7.0,\n"
            "  'layers': [\n"
            "    {'name': 'GSB', 'thickness_mm': 250},\n"
            "    {'name': 'CTB', 'thickness_mm': 200}\n"
            "  ],\n"
            "  'confidence': 0.9\n"
            "}"
        ),
        "structure_drawing": (
            "Extract structure details. Return JSON only:\n"
            "{\n"
            "  'structure_type': 'box_culvert',\n"
            "  'cells': 1, 'span_m': 3.0, 'height_m': 2.0,\n"
            "  'concrete_grade': 'M35', 'steel_grade': 'Fe550D',\n"
            "  'confidence': 0.9\n"
            "}"
        ),
    }

    prompt = prompts.get(page_type)
    if not prompt:
        return {"page_type": page_type, "confidence": 0.0, "notes": "no extractor for page type"}

    try:
        raw = _call_vision_ai(page_base64, prompt)
        parsed = _parse_json_response(raw)
        parsed["page_type"] = page_type
        return parsed
    except Exception as exc:
        return {"page_type": page_type, "confidence": 0.0, "error": str(exc)}


def merge_extractions(page_extractions: list[dict]) -> dict[str, Any]:
    """
    Merge per-page extractions into a single DrawingExtraction dict.

    Deduplicates structures by chainage and flags low-confidence items.
    """
    road_segments: list[dict] = []
    structures: list[dict] = []
    flagged: list[dict] = []
    confidences: list[float] = []
    drawing_type = "general_notes"

    seen_chainages: set[str] = set()

    try:
        for ext in page_extractions:
            page_type = ext.get("page_type", ext.get("type", ""))
            conf = float(ext.get("confidence", 0.5))
            confidences.append(conf)

            if page_type in ("plan_view", "profile_view"):
                drawing_type = page_type
            elif page_type == "typical_cross_section":
                drawing_type = "typical_cross_section"
                layers = ext.get("layers", [])
                chainages = ext.get("chainages", ["00+000", "44+000"])
                road_segments.append({
                    "chainage_start": chainages[0] if chainages else "00+000",
                    "chainage_end": chainages[-1] if len(chainages) > 1 else chainages[0] if chainages else "44+000",
                    "length_km": _chainage_length_km(chainages),
                    "tcs_type": ext.get("tcs_type", "TCS-1"),
                    "formation_width_m": float(ext.get("formation_width_m", 0)),
                    "carriageway_width_m": float(ext.get("carriageway_width_m", 0)),
                    "pavement_layers": layers,
                })

            for struct in ext.get("structures", []):
                chainage = str(struct.get("chainage", ""))
                if chainage and chainage in seen_chainages:
                    continue
                if chainage:
                    seen_chainages.add(chainage)
                entry = {
                    "id": struct.get("id", f"STR-{len(structures)+1:03d}"),
                    "type": struct.get("type", "box_culvert"),
                    "chainage": chainage,
                    "cells": int(struct.get("cells", 1)),
                    "span_m": float(struct.get("span_m", 0)),
                    "height_m": float(struct.get("height_m", 0)),
                    "length_m": float(struct.get("length_m", 25.5)),
                    "embankment": bool(struct.get("embankment", False)),
                    "concrete_grade": struct.get("concrete_grade", "M35"),
                    "steel_grade": struct.get("steel_grade", "Fe550D"),
                }
                structures.append(entry)
                if float(struct.get("confidence", conf)) < 0.75:
                    flagged.append({"chainage": chainage, "reason": "low confidence structure"})

            if page_type == "structure_drawing":
                drawing_type = "structure_drawing"
                entry = {
                    "id": f"STR-{len(structures)+1:03d}",
                    "type": ext.get("structure_type", "box_culvert"),
                    "chainage": ext.get("chainage", ""),
                    "cells": int(ext.get("cells", 1)),
                    "span_m": float(ext.get("span_m", 0)),
                    "height_m": float(ext.get("height_m", 0)),
                    "length_m": float(ext.get("length_m", 25.5)),
                    "embankment": False,
                    "concrete_grade": ext.get("concrete_grade", "M35"),
                    "steel_grade": ext.get("steel_grade", "Fe550D"),
                }
                structures.append(entry)
                if conf < 0.75:
                    flagged.append({"structure_id": entry["id"], "reason": "low confidence structure drawing"})

            if conf < 0.75:
                flagged.append({"page_type": page_type, "reason": "low confidence page"})

    except (TypeError, ValueError, KeyError) as exc:
        return {
            "drawing_type": drawing_type,
            "confidence": 0.0,
            "road_segments": road_segments,
            "structures": structures,
            "flagged_for_review": flagged,
            "extraction_confidence": 0.0,
            "error": str(exc),
        }

    avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

    return {
        "drawing_type": drawing_type,
        "confidence": avg_conf,
        "road_segments": road_segments,
        "structures": structures,
        "flagged_for_review": flagged,
        "extraction_confidence": avg_conf,
    }


def analyze_drawing(
    file_bytes: bytes,
    filename: str,
    estimation_type: str,
    use_mock_ai: bool = False,
) -> dict[str, Any]:
    """
    Main entry point: rasterize PDF, classify pages, extract data, and merge.

    Called by the drawing router. Set use_mock_ai=True for offline testing.
    """
    try:
        pages = rasterize_pdf_pages(file_bytes)
        if not pages:
            return {
                "filename": filename,
                "estimation_type": estimation_type,
                "drawing_type": "general_notes",
                "confidence": 0.0,
                "road_segments": [],
                "structures": [],
                "flagged_for_review": [{"reason": "could not rasterize PDF"}],
                "extraction_confidence": 0.0,
                "error": "rasterization failed or pdf2image unavailable",
            }

        page_extractions: list[dict] = []
        for page in pages[:10]:
            classification = classify_page(page["base64"], page["page_num"], mock=use_mock_ai)
            page_type = classification.get("type", "general_notes")
            extraction = extract_from_page(page["base64"], page_type, mock=use_mock_ai)
            extraction["page_type"] = page_type
            extraction["confidence"] = float(extraction.get("confidence", classification.get("confidence", 0.5)))
            page_extractions.append(extraction)

        merged = merge_extractions(page_extractions)
        merged["filename"] = filename
        merged["estimation_type"] = estimation_type
        merged["pages_analyzed"] = len(pages)
        return merged

    except Exception as exc:
        return {
            "filename": filename,
            "estimation_type": estimation_type,
            "drawing_type": "general_notes",
            "confidence": 0.0,
            "road_segments": [],
            "structures": [],
            "flagged_for_review": [{"reason": str(exc)}],
            "extraction_confidence": 0.0,
            "error": str(exc),
        }


def _chainage_length_km(chainages: list[str]) -> float:
    """Estimate road length in km from first and last chainage strings."""
    try:
        if len(chainages) < 2:
            return 0.0
        start = _chainage_to_metres(chainages[0])
        end = _chainage_to_metres(chainages[-1])
        return round(abs(end - start) / 1000, 2)
    except (TypeError, ValueError):
        return 0.0


def _chainage_to_metres(chainage: str) -> float:
    chainage = chainage.replace(" ", "")
    if "+" in chainage:
        parts = chainage.split("+")
        return float(parts[0]) * 1000 + float(parts[1])
    return float(chainage)


def extract_text_layer(file_bytes: bytes) -> dict:
    import pdfplumber, io
    pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            words = page.extract_words() or []
            pages.append({
                "page_num": i,
                "text": text,
                "word_count": len(words),
                "has_meaningful_text": len(text.strip()) > 50
            })
    return {
        "total_pages": len(pages),
        "pages_with_text": sum(1 for p in pages if p["has_meaningful_text"]),
        "pages": pages
    }
