from io import BytesIO

from PIL import Image

from database import get_screening_history, init_db
from services import ocr
from services.pipeline import run_screening


def test_pipeline_completes_and_saves_history_without_external_models(tmp_path, monkeypatch):
    database_path = tmp_path / "registry.db"
    init_db(database_path)
    monkeypatch.setattr(ocr, "_get_paddle_engine", lambda: None)
    monkeypatch.setattr(ocr, "_paddle_error", "disabled in test")

    buffer = BytesIO()
    Image.new("RGB", (160, 120), "white").save(buffer, format="PNG")
    transcript = "\n".join(
        [
            "CERTIFICATE",
            "Certificate ID: CERT001",
            "Name: ARUN KUMAR",
            "Register No: 21CS001",
            "Institution: FICTIONAL DEMO INSTITUTE",
            "CGPA: 9.0",
        ]
    )
    events = []
    result = run_screening(
        buffer.getvalue(),
        "synthetic-certificate.png",
        manual_text=transcript,
        on_step=events.append,
        db_path=database_path,
    )

    assert result["document_type"] == "CERTIFICATE"
    assert result["fields"]["document_number"] == "CERT001"
    assert result["trusted_match"]["record_found"]
    assert result["risk"]["score"] <= 100
    assert result["history_id"]
    assert len(events) == 14
    assert len(get_screening_history(db_path=database_path)) == 1


def test_pipeline_requires_review_when_ocr_is_unavailable(tmp_path, monkeypatch):
    database_path = tmp_path / "registry.db"
    init_db(database_path)
    monkeypatch.setattr(ocr, "_get_paddle_engine", lambda: None)
    monkeypatch.setattr(ocr, "_paddle_error", "disabled in test")
    buffer = BytesIO()
    Image.new("RGB", (120, 100), "white").save(buffer, format="PNG")

    result = run_screening(buffer.getvalue(), "unreadable.png", db_path=database_path)

    assert result["final_status"] == "REVIEW REQUIRED"
    assert result["risk"]["review_required"]
    assert any("OCR text was unavailable" in reason for reason in result["risk"]["reasons"])


def test_synthetic_demo_certificate_completes_full_pipeline(tmp_path, monkeypatch):
    database_path = tmp_path / "registry.db"
    init_db(database_path)
    monkeypatch.setattr(ocr, "_get_paddle_engine", lambda: None)
    monkeypatch.setattr(ocr, "_paddle_error", "Application Control blocked PaddleOCR")
    monkeypatch.setattr(ocr.shutil, "which", lambda _: None)
    sample_path = ocr.DEMO_CERTIFICATE_PATH
    events = []

    result = run_screening(
        sample_path.read_bytes(),
        sample_path.name,
        on_step=events.append,
        db_path=database_path,
    )

    assert result["ocr"]["status"] == "DEMO"
    assert result["ocr"]["engine"] == "Demo OCR Fallback"
    assert result["fields"]["document_number"] == "CERT001"
    assert result["fields"]["name"] == "ARUN KUMAR"
    assert result["fields"]["register_number"] == "21CS001"
    assert result["fields"]["cgpa"] == "9.0"
    assert result["trusted_match"]["record_found"]
    assert result["validation"]["status"] == "PASS"
    assert result["tampering"]["status"] == "ANALYZED"
    assert result["face"]["status"] == "NOT_AVAILABLE"
    assert 0 <= result["risk"]["score"] <= 100
    assert result["history_id"]
    assert len(events) == 14
    assert len(get_screening_history(db_path=database_path)) == 1
