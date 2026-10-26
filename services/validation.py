import re
from datetime import date, datetime


REQUIRED_FIELDS = {
	"PASSPORT": ("name", "document_number", "date_of_birth", "nationality", "expiry_date"),
	"VISA": ("name", "document_number", "expiry_date"),
	"ID_CARD": ("name", "document_number", "date_of_birth"),
	"CERTIFICATE": ("name", "document_number", "register_number"),
	"PERMIT": ("name", "document_number", "expiry_date"),
	"UNKNOWN": ("name", "document_number"),
}


def _parse_date(value):
	if not value:
		return None
	for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d"):
		try:
			return datetime.strptime(str(value).strip(), date_format).date()
		except ValueError:
			continue
	return None


def validate_document(fields, document_type="UNKNOWN", trusted_match=None, today=None):
	"""Run conservative format, required-field, date, and registry-status checks."""
	fields = fields or {}
	today = today or date.today()
	passed = []
	failed = []
	warnings = []
	document_type = document_type if document_type in REQUIRED_FIELDS else "UNKNOWN"

	for field in REQUIRED_FIELDS[document_type]:
		if fields.get(field) in (None, ""):
			failed.append(f"Required {field.replace('_', ' ')} was not extracted.")
		else:
			passed.append(f"{field.replace('_', ' ').title()} is present.")

	document_number = fields.get("document_number")
	if document_number:
		if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9/-]{2,24}", str(document_number).strip()):
			passed.append("Document number format looks plausible.")
		else:
			failed.append("Document number has an unexpected format.")

	for field in ("date_of_birth", "expiry_date", "issue_date"):
		value = fields.get(field)
		if not value:
			continue
		parsed = _parse_date(value)
		if parsed is None:
			failed.append(f"{field.replace('_', ' ').title()} is not a recognized date.")
		elif field == "date_of_birth" and parsed > today:
			failed.append("Date of birth is in the future.")
		elif field == "expiry_date" and parsed < today:
			failed.append("Document expiry date has passed.")
		elif field == "expiry_date":
			passed.append("Document expiry date has not passed.")
		else:
			passed.append(f"{field.replace('_', ' ').title()} is a valid date.")

	if trusted_match and trusted_match.get("record_found"):
		status = str(trusted_match.get("database_status", "")).upper()
		if status == "VALID":
			passed.append("Trusted demo record status is VALID.")
		else:
			failed.append(f"Trusted demo record status is {status or 'UNKNOWN'}.")
		for field, values in trusted_match.get("mismatched_fields", {}).items():
			failed.append(f"{field.replace('_', ' ').title()} differs from the trusted demo record.")
	else:
		warnings.append("Trusted reference record unavailable; this is not proof of fraud.")

	return {
		"status": "FAILED" if failed else "WARNING" if warnings else "PASS",
		"passed_checks": passed,
		"failed_checks": failed,
		"warnings": warnings,
		"expiry_valid": not any("expiry date has passed" in item.lower() for item in failed),
	}
