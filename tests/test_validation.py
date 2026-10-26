from datetime import date

from services.validation import validate_document


def test_valid_fictional_certificate_passes():
    fields = {
        "name": "ARUN KUMAR",
        "document_number": "CERT001",
        "register_number": "21CS001",
        "cgpa": "9.0",
    }
    trusted = {
        "record_found": True,
        "database_status": "VALID",
        "matched_fields": ["name", "document_number"],
        "mismatched_fields": {},
    }
    result = validate_document(fields, "CERTIFICATE", trusted, today=date(2026, 1, 1))
    assert result["status"] == "PASS"
    assert result["failed_checks"] == []


def test_passport_expiry_and_bad_date_are_reported():
    fields = {
        "name": "DEMO PERSON",
        "document_number": "P1234567",
        "date_of_birth": "not-a-date",
        "nationality": "FICTIONAL",
        "expiry_date": "2020-01-01",
    }
    result = validate_document(fields, "PASSPORT", today=date(2026, 1, 1))
    assert any("not a recognized date" in item for item in result["failed_checks"])
    assert any("expiry date has passed" in item for item in result["failed_checks"])


def test_missing_registry_is_warning_not_validation_failure():
    result = validate_document(
        {"name": "DEMO PERSON", "document_number": "DOC123"},
        "UNKNOWN",
        {"record_found": False},
    )
    assert result["status"] == "WARNING"
    assert result["failed_checks"] == []
    assert result["warnings"]
