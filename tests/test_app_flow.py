from pathlib import Path

from streamlit.testing.v1 import AppTest

import services.pipeline as pipeline
from database import get_screening_history, init_db


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_CERTIFICATE = PROJECT_ROOT / "sample_data" / "genuine" / "veridoc_demo_certificate.png"


def test_demo_certificate_completes_streamlit_three_screen_flow(tmp_path, monkeypatch):
    database_path = tmp_path / "registry.db"
    init_db(database_path)
    original_run_screening = pipeline.run_screening

    def run_with_temporary_database(*args, **kwargs):
        kwargs["db_path"] = database_path
        return original_run_screening(*args, **kwargs)

    monkeypatch.setattr(pipeline, "run_screening", run_with_temporary_database)
    app = AppTest.from_file(str(PROJECT_ROOT / "app.py")).run(timeout=10)
    assert not app.exception
    assert app.session_state["screen"] == "upload"

    app.file_uploader[0].upload(
        DEMO_CERTIFICATE.name,
        DEMO_CERTIFICATE.read_bytes(),
        "image/png",
    ).run(timeout=10)
    app.button(key="start_verification").click().run(timeout=20)

    assert not app.exception
    assert app.session_state["screen"] == "result"
    result = app.session_state["screening_result"]
    assert result["ocr"]["status"] == "DEMO"
    assert result["ocr"]["engine"] == "Demo OCR Fallback"
    assert result["fields"]["document_number"] == "CERT001"
    assert result["fields"]["name"] == "ARUN KUMAR"
    assert result["trusted_match"]["record_found"]
    assert result["validation"]["status"] == "PASS"
    assert result["tampering"]["status"] == "ANALYZED"
    assert result["face"]["status"] == "NOT_AVAILABLE"
    assert 0 <= result["risk"]["score"] <= 100
    assert any("Demo OCR Fallback" in str(item.value) for item in app.info)
    assert len(app.text_area) == 0
    assert len(get_screening_history(db_path=database_path)) == 1
