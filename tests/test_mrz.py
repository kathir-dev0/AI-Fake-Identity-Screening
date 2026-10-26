from services.mrz_validator import _check_digit, validate_mrz


def build_td3_sample():
    line_one = ("P<UTO" + "DEMO<<TEST").ljust(44, "<")
    passport_number = "X12345678"
    birth_date = "900101"
    expiry_date = "300101"
    personal_number = "12345678901234"
    line_two = (
        passport_number
        + _check_digit(passport_number)
        + "UTO"
        + birth_date
        + _check_digit(birth_date)
        + "F"
        + expiry_date
        + _check_digit(expiry_date)
        + personal_number
        + _check_digit(personal_number)
    )
    composite = line_two[0:10] + line_two[13:20] + line_two[21:43]
    line_two += _check_digit(composite)
    assert len(line_one) == len(line_two) == 44
    return line_one + "\n" + line_two


def test_td3_check_digits_and_visible_fields_match():
    result = validate_mrz(
        build_td3_sample(),
        {
            "document_number": "X12345678",
            "name": "TEST DEMO",
            "nationality": "UTO",
            "gender": "F",
            "date_of_birth": "1990-01-01",
            "expiry_date": "2030-01-01",
        },
    )
    assert result["status"] == "VALID"
    assert all(check["passed"] for check in result["checks"])
    assert result["mismatches"] == []


def test_mrz_reports_visible_field_mismatch():
    result = validate_mrz(build_td3_sample(), {"nationality": "FICTIONAL"})
    assert result["status"] == "INCONSISTENT"
    assert "nationality" in result["mismatches"]


def test_absent_mrz_is_not_available():
    assert validate_mrz("ordinary text")['status'] == "NOT_AVAILABLE"
