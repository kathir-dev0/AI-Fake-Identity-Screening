RISK_THRESHOLDS = (
    (24, "LOW RISK"),
    (49, "MEDIUM RISK"),
    (74, "REVIEW REQUIRED"),
    (100, "HIGH RISK"),
)

FACE_MISMATCH_THRESHOLD = 0.40


def _bounded_number(value, minimum=0.0, maximum=1.0):
    try:
        return min(maximum, max(minimum, float(value)))
    except (TypeError, ValueError):
        return None


def _risk_level(score):
    for upper_bound, label in RISK_THRESHOLDS:
        if score <= upper_bound:
            return label
    return RISK_THRESHOLDS[-1][1]


def calculate_risk(
    trusted_match=None,
    validation=None,
    mrz=None,
    tampering=None,
    face=None,
    ocr=None,
):
    """Calculate a deterministic 0-100 risk score from screening service outputs."""
    trusted_match = trusted_match or {}
    validation = validation or {}
    mrz = mrz or {"status": "NOT_AVAILABLE"}
    tampering = tampering or {"tampering_score": 0.0, "level": "NOT_AVAILABLE"}
    face = face or {"status": "NOT_AVAILABLE", "match": None}
    ocr = ocr or {"status": "NOT_AVAILABLE", "confidences": []}
    breakdown = {}
    reasons = []

    mismatches = trusted_match.get("mismatched_fields", {}) or {}
    mismatch_count = len(mismatches)
    critical_fields = {"name", "document_number", "certificate_id", "register_number"}
    critical_mismatch = bool(critical_fields.intersection(mismatches))
    if mismatch_count:
        base_points = 30 if critical_mismatch else 25
        field_points = min(40, base_points + 5 * (mismatch_count - 1))
        fields = ", ".join(sorted(mismatches))
        reasons.append(f"Trusted-reference mismatch in {mismatch_count} field(s): {fields}.")
    else:
        field_points = 0
    breakdown["field_mismatches"] = field_points

    raw_failures = validation.get("failed_checks", []) or []
    validation_failures = [
        failure
        for failure in raw_failures
        if "differs from the trusted demo record" not in failure.lower()
        and "expiry date has passed" not in failure.lower()
        and "trusted demo record status is" not in failure.lower()
    ]
    validation_points = min(15, 5 * len(validation_failures))
    breakdown["validation_failures"] = validation_points
    if validation_failures:
        reasons.extend(validation_failures)

    registry_status = str(trusted_match.get("database_status", "")).strip().upper()
    if registry_status in {"REVOKED", "BLACKLISTED"}:
        status_points = 15
        reasons.append(f"Trusted record status is {registry_status}.")
    elif registry_status == "EXPIRED":
        status_points = 10
        reasons.append("Trusted record status is EXPIRED.")
    elif trusted_match.get("record_found") and registry_status not in {"", "VALID"}:
        status_points = 10
        reasons.append(f"Trusted record has an unrecognized status: {registry_status}.")
    else:
        status_points = 0
    breakdown["document_status"] = status_points

    expiry_valid = validation.get("expiry_valid")
    expiry_points = 8 if expiry_valid is False else 0
    breakdown["expiry_validity"] = expiry_points
    if expiry_points:
        reasons.append("Document expiry validation failed.")

    mrz_status = str(mrz.get("status", "NOT_AVAILABLE")).upper()
    mrz_points = 15 if mrz_status == "INCONSISTENT" else 0
    breakdown["mrz_inconsistency"] = mrz_points
    if mrz_points:
        reasons.append("Passport MRZ checks or visible-field comparison are inconsistent.")

    tampering_score = _bounded_number(tampering.get("tampering_score", 0.0)) or 0.0
    tampering_points = round(tampering_score * 20)
    breakdown["tampering_indicators"] = tampering_points
    if tampering_points:
        indication = str(tampering.get("level", "unknown")).replace("_", " ").lower()
        reasons.append(
            f"Possible manipulation indicators: {indication} ({tampering_score:.2f}/1)."
        )

    face_similarity = _bounded_number(face.get("similarity"))
    face_compared = str(face.get("status", "")).upper() == "COMPARED"
    face_mismatch = face_compared and (
        face.get("match") is False
        or (face.get("match") is None and face_similarity is not None and face_similarity < FACE_MISMATCH_THRESHOLD)
    )
    face_points = 15 if face_mismatch else 0
    breakdown["face_verification"] = face_points
    if face_mismatch:
        reasons.append(
            "Face verification did not match the available reference."
            if face_similarity is None
            else f"Face similarity {face_similarity:.2f} is below the demo threshold."
        )
    elif face_compared and face_similarity is not None:
        reasons.append(f"Face similarity measured at {face_similarity:.2f} against the demo reference.")

    registry_missing = not trusted_match.get("record_found", False)
    reference_points = 5 if registry_missing else 0
    breakdown["reference_record_missing"] = reference_points
    if registry_missing:
        reasons.append("Trusted reference record unavailable; this is a review warning, not proof of fraud.")

    confidence_values = [
        value
        for raw_value in (ocr.get("confidences", []) or [])
        if (value := _bounded_number(raw_value)) is not None
    ]
    if confidence_values:
        average_confidence = sum(confidence_values) / len(confidence_values)
        confidence_points = 8 if average_confidence < 0.50 else 5 if average_confidence < 0.75 else 0
        if confidence_points:
            reasons.append(f"Average OCR confidence is low ({average_confidence:.2f}).")
    else:
        confidence_points = 0
    breakdown["ocr_confidence"] = confidence_points

    for field in trusted_match.get("matched_fields", []) or []:
        reasons.append(f"{field.replace('_', ' ').title()} matched trusted demo record.")
    for warning in validation.get("warnings", []) or []:
        if warning not in reasons:
            reasons.append(warning)

    score = min(100, max(0, sum(breakdown.values())))
    risk_level = _risk_level(score)
    if score >= 75:
        final_status = "SUSPICIOUS INDICATORS DETECTED"
    elif score >= 25 or validation_failures or critical_mismatch or status_points or expiry_points or mrz_points or face_mismatch:
        final_status = "REVIEW REQUIRED"
    else:
        final_status = "SCREENING INDICATES NO MAJOR ANOMALIES"

    if not reasons:
        reasons.append("No scored anomalies were found in the checks that were available.")

    return {
        "score": score,
        "risk_level": risk_level,
        "final_status": final_status,
        "reasons": reasons,
        "breakdown": breakdown,
    }