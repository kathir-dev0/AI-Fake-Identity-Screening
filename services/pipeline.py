import io
from pathlib import Path

from PIL import Image, ImageOps

from config import DB_PATH
from database import compare_with_trusted, init_db, save_screening_result
from services.document_detector import detect_document_type
from services.face_verification import verify_face
from services.field_extractor import extract_fields
from services.mrz_validator import validate_mrz
from services.ocr import extract_text
from services.risk_score import calculate_risk
from services.tampering import analyze_tampering
from services.validation import validate_document


PIPELINE_STEPS = [
    "Reading document",
    "Extracting information",
    "Checking trusted reference",
    "Validating document",
    "Detecting tampering",
    "Verifying identity",
    "Calculating risk",
]


def _emit(on_step, index, status, detail=""):
    if on_step:
        try:
            on_step({"index": index, "label": PIPELINE_STEPS[index], "status": status, "detail": detail})
        except Exception:
            pass


def _prepare_image(file_bytes, filename):
    if str(filename).lower().endswith(".pdf"):
        import fitz

        document = fitz.open(stream=file_bytes, filetype="pdf")
        if not document.page_count:
            raise ValueError("The PDF contains no pages.")
        page = document.load_page(0)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    else:
        image = Image.open(io.BytesIO(file_bytes))
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((2400, 2400))
    return image


def run_screening(file_bytes, filename="document.png", manual_text="", on_step=None, db_path=DB_PATH):
    """Run all available checks and save an audit row; optional engines fail safely."""
    result = {
        "filename": Path(filename).name,
        "document_type": "UNKNOWN",
        "document_detection": {"document_type": "UNKNOWN", "confidence": 0.0, "evidence": []},
        "ocr": {
            "full_text": "",
            "lines": [],
            "confidence": None,
            "engine": None,
            "error": None,
            "text": "",
            "boxes": [],
            "confidences": [],
            "status": "ERROR",
        },
        "fields": {},
        "trusted_match": {},
        "validation": {},
        "mrz": {"status": "NOT_AVAILABLE", "checks": [], "mismatches": [], "message": "MRZ was not analyzed."},
        "tampering": {"status": "NOT_AVAILABLE", "tampering_score": 0.0, "level": "NOT_AVAILABLE", "suspicious_regions": [], "message": "Image was not analyzed."},
        "face": {"status": "NOT_AVAILABLE", "face_detected": None, "similarity": None, "match": None, "reason": "Face was not analyzed."},
        "risk": {},
        "processing_issues": [],
    }

    _emit(on_step, 0, "running")
    image = None
    try:
        image = _prepare_image(file_bytes, filename)
        result["preview_image"] = image
        result["document_detection"] = detect_document_type("", filename)
        result["document_type"] = result["document_detection"]["document_type"]
        _emit(on_step, 0, "complete", "Image prepared.")
    except Exception as error:
        result["processing_issues"].append(f"Document could not be opened: {error}")
        result["ocr"]["error"] = f"Document could not be opened: {error}"
        _emit(on_step, 0, "warning", str(error))

    _emit(on_step, 1, "running")
    if image is not None:
        result["ocr"] = extract_text(image)
    else:
        result["ocr"].update(
            {
                "status": "ERROR",
                "error": "No readable image was available.",
            }
        )
    if manual_text and manual_text.strip():
        result["ocr"].update(
            {
                "text": manual_text.strip(),
                "full_text": manual_text.strip(),
                "lines": manual_text.strip().splitlines(),
                "confidence": None,
                "status": "MANUAL",
                "engine": "Manual transcription",
                "error": None,
            }
        )
    recognized_text = result["ocr"].get("full_text") or result["ocr"].get("text", "")
    result["document_detection"] = detect_document_type(recognized_text, filename)
    result["document_type"] = result["document_detection"]["document_type"]
    result["fields"] = extract_fields(recognized_text, result["document_type"])
    _emit(
        on_step,
        1,
        "complete" if recognized_text else "warning",
        result["ocr"].get("engine") or result["ocr"].get("error") or "No text detected.",
    )

    _emit(on_step, 2, "running")
    try:
        result["trusted_match"] = compare_with_trusted(
            result["fields"], result["document_type"], db_path=db_path
        )
    except Exception as error:
        result["trusted_match"] = {
            "record_found": False,
            "matched_fields": [],
            "mismatched_fields": {},
            "database_status": "UNAVAILABLE",
            "record": None,
            "message": f"Trusted demo lookup unavailable: {error}",
        }
        result["processing_issues"].append(result["trusted_match"]["message"])
    _emit(on_step, 2, "complete", result["trusted_match"].get("message", "Lookup complete."))

    _emit(on_step, 3, "running")
    result["validation"] = validate_document(
        result["fields"], result["document_type"], result["trusted_match"]
    )
    _emit(on_step, 3, "complete", result["validation"].get("status", "Complete."))

    _emit(on_step, 4, "running")
    result["mrz"] = validate_mrz(recognized_text, result["fields"])
    if image is not None:
        result["tampering"] = analyze_tampering(image)
    else:
        result["tampering"] = analyze_tampering(None)
    _emit(on_step, 4, "complete", result["tampering"].get("level", "Unavailable."))

    _emit(on_step, 5, "running")
    trusted_record = result["trusted_match"].get("record") or {}
    result["face"] = verify_face(image, trusted_record.get("reference_face"))
    _emit(on_step, 5, "complete", result["face"].get("reason", "Unavailable."))

    _emit(on_step, 6, "running")
    result["risk"] = calculate_risk(
        result["trusted_match"],
        result["validation"],
        result["mrz"],
        result["tampering"],
        result["face"],
        ocr=result["ocr"],
    )
    if result["ocr"].get("status") not in {"OK", "MANUAL", "DEMO"}:
        incomplete_reason = "OCR text was unavailable; the screening is incomplete and requires manual review."
        result["risk"]["final_status"] = "REVIEW REQUIRED"
        result["risk"]["review_required"] = True
        if incomplete_reason not in result["risk"]["reasons"]:
            result["risk"]["reasons"].append(incomplete_reason)
    result["final_status"] = result["risk"]["final_status"]
    try:
        init_db(db_path)
        result["history_id"] = save_screening_result(result, filename, db_path)
    except Exception as error:
        result["history_error"] = f"Screening completed, but history could not be saved: {error}"
        result["processing_issues"].append(result["history_error"])
    _emit(on_step, 6, "complete", f"{result['risk']['risk_level']} · {result['risk']['score']}/100")
    return result
