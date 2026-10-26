"""
OCR Service Module
SIH Problem Statement: SIH26188 (AI-Based Fake Identity & Document Screening System)

Handles text extraction from document images using PaddleOCR.
Features:
- Cached OCR model loading to prevent redundant re-initialization.
- Support for multiple image formats (PIL Image, numpy array).
- Unified parsing across PaddleOCR v2 and v3 response formats.
- Safe execution with comprehensive error handling.
"""

from typing import Dict, Any, List
import numpy as np
from PIL import Image
import streamlit as st

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False


@st.cache_resource(show_spinner="Loading PaddleOCR model (one-time initialization)...")
def get_ocr_engine():
    """
    Initializes and caches the PaddleOCR engine.
    Uses `@st.cache_resource` so the model is instantiated only once across reruns.
    """
    if not PADDLE_AVAILABLE:
        raise ImportError(
            "PaddleOCR is not installed. Please install it using: "
            "`pip install paddlepaddle>=3.0.0 paddleocr>=3.0.0`"
        )

    # Note: `enable_mkldnn=False` prevents PIR runtime compatibility issues on Windows
    try:
        return PaddleOCR(
            lang="en",
            enable_mkldnn=False
        )
    except Exception:
        # Fallback if arguments differ in future or legacy versions
        return PaddleOCR(lang="en")


def parse_ocr_output(raw_results) -> List[Dict[str, Any]]:
    """
    Normalizes OCR results across PaddleOCR v3 (dict output) and v2 (nested list output).

    Returns a list of dicts:
    [
        {"text": "EXTRACTED_LINE", "confidence": 0.98},
        ...
    ]
    """
    extracted_lines: List[Dict[str, Any]] = []
    if not raw_results:
        return extracted_lines

    for item in raw_results:
        # PaddleOCR v3.x format: list of dicts containing 'rec_texts' and 'rec_scores'
        if isinstance(item, dict):
            texts = item.get("rec_texts", [])
            scores = item.get("rec_scores", [])
            for text, score in zip(texts, scores):
                text_clean = str(text).strip()
                if text_clean:
                    conf = float(score) if score is not None else 1.0
                    extracted_lines.append({
                        "text": text_clean,
                        "confidence": round(conf, 4)
                    })

        # PaddleOCR v2.x format: [ [ [box], (text, score) ], ... ]
        elif isinstance(item, list):
            for line_item in item:
                if isinstance(line_item, (list, tuple)) and len(line_item) >= 2:
                    text_data = line_item[1]
                    if isinstance(text_data, (list, tuple)) and len(text_data) >= 2:
                        txt, score = text_data[0], text_data[1]
                        if txt and str(txt).strip():
                            extracted_lines.append({
                                "text": str(txt).strip(),
                                "confidence": round(float(score), 4) if score is not None else 1.0
                            })
                    elif isinstance(text_data, str) and text_data.strip():
                        extracted_lines.append({
                            "text": text_data.strip(),
                            "confidence": 1.0
                        })

    return extracted_lines


def extract_document_text(image_input) -> Dict[str, Any]:
    """
    Extracts text and confidence scores from an uploaded document image.

    Args:
        image_input: PIL.Image.Image or numpy.ndarray

    Returns:
        A dictionary containing:
        - "success": bool
        - "lines": List[Dict[str, Any]] (each with "text" and "confidence")
        - "full_text": str (all lines joined by newline)
        - "line_count": int
        - "avg_confidence": float
        - "error": Optional[str]
    """
    if not PADDLE_AVAILABLE:
        return {
            "success": False,
            "lines": [],
            "full_text": "",
            "line_count": 0,
            "avg_confidence": 0.0,
            "error": "PaddleOCR is not installed in the environment."
        }

    try:
        # Convert PIL Image to RGB numpy array
        if isinstance(image_input, Image.Image):
            rgb_image = image_input.convert("RGB")
            img_np = np.array(rgb_image)
        elif isinstance(image_input, np.ndarray):
            img_np = image_input
            if len(img_np.shape) == 2:
                img_np = np.stack([img_np] * 3, axis=-1)
            elif img_np.shape[2] == 4:
                img_np = img_np[:, :, :3]
        else:
            return {
                "success": False,
                "lines": [],
                "full_text": "",
                "line_count": 0,
                "avg_confidence": 0.0,
                "error": f"Unsupported image input type: {type(image_input)}"
            }

        # Retrieve cached OCR engine
        engine = get_ocr_engine()

        # Run inference using predict (v3) with fallback to ocr (v2)
        if hasattr(engine, "predict"):
            raw_output = list(engine.predict(img_np))
        else:
            raw_output = engine.ocr(img_np)

        lines = parse_ocr_output(raw_output)
        full_text = "\n".join([line["text"] for line in lines])
        avg_conf = (
            round(sum(line["confidence"] for line in lines) / len(lines), 4)
            if lines else 0.0
        )

        return {
            "success": True,
            "lines": lines,
            "full_text": full_text,
            "line_count": len(lines),
            "avg_confidence": avg_conf,
            "error": None
        }

    except Exception as exc:
        return {
            "success": False,
            "lines": [],
            "full_text": "",
            "line_count": 0,
            "avg_confidence": 0.0,
            "error": str(exc)
        }
