import re
from datetime import datetime


LABELS = {
    "document_number": r"(?:document\s*(?:no|number)|passport\s*(?:no|number)|visa\s*(?:no|number)|permit\s*(?:no|number)|certificate\s*(?:id|no|number)|certificate\s*number|id\s*(?:no|number))",
    "certificate_id": r"certificate\s*(?:id|no|number)",
    "register_number": r"(?:register|registration|student)\s*(?:no|number|id)",
    "name": r"(?:full\s*name|name|student\s*name|holder)\s*",
    "date_of_birth": r"(?:date\s*of\s*birth|birth\s*date|dob)",
    "nationality": r"nationality",
    "gender": r"(?:sex|gender)",
    "expiry_date": r"(?:date\s*of\s*expiry|expiry\s*date|expiration\s*date|expires?)",
    "institution": r"(?:institution|university|college|school)",
    "cgpa": r"(?:cgpa|gpa|grade\s*point|grade)",
    "issue_date": r"(?:issue\s*date|date\s*of\s*issue)",
    "course": r"(?:course|program|programme)",
}


def _value_after_label(line, label_pattern):
    match = re.match(rf"^\s*(?:{label_pattern})\s*[:#=-]?\s*(.*?)\s*$", line, re.IGNORECASE)
    if match:
        value = match.group(1).strip(" :#=-")
        return value or None
    return None


def _normalize_date(value):
    if not value:
        return value
    value = value.strip()
    formats = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d")
    for date_format in formats:
        try:
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            continue
    return value


def extract_fields(text, document_type="UNKNOWN"):
    """Extract labeled fields conservatively; values are left unset when unclear."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    fields = {"document_type": document_type}
    for line in lines:
        for key, label_pattern in LABELS.items():
            value = _value_after_label(line, label_pattern)
            if value:
                if key in {"document_number", "certificate_id", "register_number"}:
                    value = re.sub(r"\s+", "", value).upper()
                elif key in {"name", "nationality", "gender", "institution", "course"}:
                    value = re.sub(r"\s+", " ", value).strip().upper()
                elif key == "cgpa":
                    number = re.search(r"\d+(?:\.\d+)?", value)
                    value = number.group(0) if number else value
                elif key in {"date_of_birth", "expiry_date", "issue_date"}:
                    value = _normalize_date(value)
                fields[key] = value

    if fields.get("certificate_id") and not fields.get("document_number"):
        fields["document_number"] = fields["certificate_id"]
    if not fields.get("document_number"):
        fallback_patterns = {
            "PASSPORT": r"\b[A-Z][0-9]{6,9}\b",
            "CERTIFICATE": r"\bCERT[0-9A-Z-]{2,}\b",
            "VISA": r"\bVISA[0-9A-Z-]{2,}\b",
        }
        pattern = fallback_patterns.get(document_type)
        if pattern:
            match = re.search(pattern, "\n".join(lines), re.IGNORECASE)
            if match:
                fields["document_number"] = match.group(0).upper()
                if document_type == "CERTIFICATE":
                    fields["certificate_id"] = fields["document_number"]
    return fields
