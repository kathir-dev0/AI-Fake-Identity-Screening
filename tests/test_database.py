from database import (
    compare_with_trusted,
    find_trusted_document,
    get_screening_history,
    init_db,
    save_screening_result,
)


def test_database_creates_demo_records_and_history_table(tmp_path):
    path = tmp_path / "registry.db"
    init_db(path)
    record = find_trusted_document("CERT001", path)
    assert record["name"] == "ARUN KUMAR"
    assert record["register_number"] == "21CS001"
    assert record["cgpa"] == "9.0"


def test_compare_reports_matches_and_mismatches(tmp_path):
    path = tmp_path / "registry.db"
    init_db(path)
    match = compare_with_trusted(
        {"document_number": "CERT001", "name": "ARUN KUMAR", "register_number": "21CS001"},
        "CERTIFICATE",
        path,
    )
    assert match["record_found"]
    assert {"document_number", "name", "register_number"} <= set(match["matched_fields"])

    altered = compare_with_trusted(
        {"document_number": "CERT001", "name": "SYNTHETIC OTHER", "register_number": "21CS001"},
        "CERTIFICATE",
        path,
    )
    assert altered["mismatched_fields"]["name"]["trusted"] == "ARUN KUMAR"


def test_unknown_reference_is_not_called_fake(tmp_path):
    path = tmp_path / "registry.db"
    init_db(path)
    result = compare_with_trusted({"document_number": "UNKNOWN-000"}, "CERTIFICATE", path)
    assert not result["record_found"]
    assert "not mean the document is fake" in result["message"]


def test_screening_history_is_saved(tmp_path):
    path = tmp_path / "registry.db"
    init_db(path)
    result = {
        "document_type": "CERTIFICATE",
        "fields": {"document_number": "CERT001"},
        "risk": {"score": 12, "risk_level": "LOW RISK", "reasons": ["Synthetic test"]},
        "final_status": "SCREENING INDICATES NO MAJOR ANOMALIES",
    }
    save_screening_result(result, "demo.png", path)
    history = get_screening_history(db_path=path)
    assert len(history) == 1
    assert history[0]["filename"] == "demo.png"
    assert history[0]["risk_score"] == 12
