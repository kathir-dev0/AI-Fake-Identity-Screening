import pytest

from services.risk_score import _risk_level, calculate_risk


def clean_match():
    return {
        "record_found": True,
        "database_status": "VALID",
        "matched_fields": ["name", "document_number", "date_of_birth"],
        "mismatched_fields": {},
    }


def clean_validation():
    return {"expiry_valid": True, "failed_checks": [], "warnings": []}


def test_low_risk_when_checks_match():
    result = calculate_risk(
        clean_match(),
        clean_validation(),
        {"status": "VALID"},
        {"tampering_score": 0.1, "level": "LOW INDICATION"},
        {"status": "COMPARED", "match": True, "similarity": 0.91},
        {"status": "OK", "confidences": [0.94, 0.96]},
    )
    assert 0 <= result["score"] <= 24
    assert result["risk_level"] == "LOW RISK"


def test_single_minor_mismatch_produces_medium_risk():
    trusted = clean_match()
    trusted["mismatched_fields"] = {"nationality": {"extracted": "OTHER", "trusted": "DEMO"}}
    result = calculate_risk(
        trusted,
        clean_validation(),
        {"status": "VALID"},
        {"tampering_score": 0.0},
        {"status": "NOT_AVAILABLE", "match": None},
        {"status": "OK", "confidences": [0.95]},
    )
    assert 25 <= result["score"] <= 49
    assert result["risk_level"] == "MEDIUM RISK"


def test_multiple_inconsistencies_produce_review_required():
    trusted = clean_match()
    trusted["mismatched_fields"] = {
        "nationality": {"extracted": "OTHER", "trusted": "DEMO"},
        "institution": {"extracted": "OTHER SCHOOL", "trusted": "DEMO SCHOOL"},
    }
    result = calculate_risk(
        trusted,
        clean_validation(),
        {"status": "INCONSISTENT"},
        {"tampering_score": 0.6, "level": "MEDIUM INDICATION"},
        {"status": "NOT_AVAILABLE", "match": None},
        {"status": "OK", "confidences": [0.91]},
    )
    assert 50 <= result["score"] <= 74
    assert result["risk_level"] == "REVIEW REQUIRED"


def test_independent_high_risk_signals_produce_high_risk():
    trusted = clean_match()
    trusted.update(
        {
            "database_status": "BLACKLISTED",
            "mismatched_fields": {
                "name": {"extracted": "OTHER PERSON", "trusted": "DEMO PERSON"},
                "document_number": {"extracted": "DOC999", "trusted": "DOC001"},
            },
        }
    )
    result = calculate_risk(
        trusted,
        {"expiry_valid": False, "failed_checks": []},
        {"status": "INCONSISTENT"},
        {"tampering_score": 0.9, "level": "HIGH INDICATION"},
        {"status": "COMPARED", "match": False, "similarity": 0.2},
        {"status": "OK", "confidences": [0.2]},
    )
    assert 75 <= result["score"] <= 100
    assert result["score"] == 100
    assert result["risk_level"] == "HIGH RISK"


def test_missing_reference_and_face_data_do_not_mean_high_risk():
    result = calculate_risk(
        {"record_found": False, "mismatched_fields": {}},
        clean_validation(),
        {"status": "NOT_AVAILABLE"},
        {"tampering_score": 0.0},
        {"status": "NOT_AVAILABLE", "match": None, "similarity": None},
        {"status": "OK", "confidences": [0.95]},
    )
    assert result["score"] == 5
    assert result["breakdown"]["reference_record_missing"] == 5
    assert "not proof of fraud" in " ".join(result["reasons"])
    assert result["risk_level"] == "LOW RISK"


def test_score_never_exceeds_100():
    result = calculate_risk(
        {"record_found": True, "database_status": "BLACKLISTED", "mismatched_fields": {"name": "x"}},
        {"expiry_valid": False},
        {"status": "INCONSISTENT"},
        {"tampering_score": 50},
        {"status": "COMPARED", "match": False},
    )
    assert result["score"] <= 100


def test_score_uses_ocr_confidence_values():
    low_confidence = calculate_risk(
        clean_match(), clean_validation(), ocr={"status": "OK", "confidences": [0.2, 0.3]}
    )
    high_confidence = calculate_risk(
        clean_match(), clean_validation(), ocr={"status": "OK", "confidences": [0.9, 0.95]}
    )
    assert low_confidence["breakdown"]["ocr_confidence"] == 8
    assert high_confidence["breakdown"]["ocr_confidence"] == 0
    assert low_confidence["score"] > high_confidence["score"]


def test_critical_mismatch_requires_review():
    result = calculate_risk(
        {
            "record_found": True,
            "database_status": "VALID",
            "mismatched_fields": {"name": {"extracted": "OTHER", "trusted": "ARUN KUMAR"}},
        }
    )
    assert result["score"] == 30
    assert result["risk_level"] == "MEDIUM RISK"
    assert result["final_status"] == "REVIEW REQUIRED"


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (24, "LOW RISK"),
        (25, "MEDIUM RISK"),
        (49, "MEDIUM RISK"),
        (50, "REVIEW REQUIRED"),
        (74, "REVIEW REQUIRED"),
        (75, "HIGH RISK"),
        (100, "HIGH RISK"),
    ],
)
def test_risk_threshold_boundaries(score, expected):
    assert _risk_level(score) == expected
