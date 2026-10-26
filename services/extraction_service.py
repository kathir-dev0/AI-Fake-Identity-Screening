"""
Field Extraction Service Module
SIH Problem Statement: SIH26188 (AI-Based Fake Identity & Document Screening System)

Extracts structured identity fields from raw OCR recognized text.
Target fields:
- Full Name
- Document Number
- Nationality
- Date of Birth
- Gender
- Date of Issue
- Date of Expiry

Notes:
- Uses readable Python parsing and regex heuristics with label variation support.
- If a field is not detected, sets value strictly to "Not detected".
- Does NOT fabricate, guess, or synthesize missing values.
- Does NOT claim authenticity; strictly organizes detected text.
"""

import re
from typing import Dict, Any, List, Optional, Union


# Standard fallback indicator when field cannot be found
NOT_DETECTED = "Not detected"

# Canonical target field names in standard display order
FIELD_ORDER = [
    "Full Name",
    "Document Number",
    "Nationality",
    "Date of Birth",
    "Gender",
    "Date of Issue",
    "Date of Expiry",
]

# Common generic / noise tokens to reject as names
NAME_BLOCKLIST = {
    "test document",
    "not valid for identification",
    "specimen",
    "sample",
    "government of india",
    "republic of india",
    "identity card",
    "driving licence",
    "driving license",
    "passport",
    "national id",
    "official document",
    "signature",
    "authority",
    "document",
    "identification",
}


def _clean_str(val: Optional[str]) -> str:
    """Removes leading/trailing punctuation and extra whitespace."""
    if not val:
        return ""
    # Strip typical delimiters like colons, hyphens, pipes, quotes
    cleaned = re.sub(r"^[\s:\-\|\,\.\;]+|[\s:\-\|\,\.\;]+$", "", val.strip())
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_full_name(lines: List[str], full_text: str) -> str:
    """
    Extracts the individual's full name.
    Supports labels: 'Full Name', 'Name', 'Given Name', 'Given Names', 'Holder Name'.
    """
    label_pattern = re.compile(
        r"^(?:full\s*name|name|given\s*names?|holder(?:'s)?\s*name)\s*[:\-\s]\s*(.+)$",
        re.IGNORECASE
    )
    standalone_label = re.compile(
        r"^(?:full\s*name|name|given\s*names?|holder(?:'s)?\s*name)\s*[:\-]?$",
        re.IGNORECASE
    )

    # 1. Check line-by-line
    for i, line in enumerate(lines):
        line_clean = line.strip()
        match = label_pattern.match(line_clean)
        if match:
            candidate = _clean_str(match.group(1))
            if candidate.lower() not in NAME_BLOCKLIST and len(candidate) >= 2:
                return candidate

        # Check multi-line: label on line i, value on line i+1
        if standalone_label.match(line_clean) and i + 1 < len(lines):
            next_line = _clean_str(lines[i + 1])
            if next_line.lower() not in NAME_BLOCKLIST and len(next_line) >= 2:
                # Ensure next line isn't another field label
                if not any(next_line.lower().startswith(prefix) for prefix in [
                    "doc", "nat", "date", "dob", "gen", "sex", "exp", "iss"
                ]):
                    return next_line

    # 2. Fallback search across full text
    fallback_match = re.search(
        r"(?:full\s*name|holder(?:'s)?\s*name|name)\s*[:\-\s]\s*([A-Za-z\s\.\'\-]+)",
        full_text,
        re.IGNORECASE
    )
    if fallback_match:
        candidate = _clean_str(fallback_match.group(1))
        # Take only the first line if multi-line captured
        candidate = candidate.split("\n")[0].strip()
        if candidate.lower() not in NAME_BLOCKLIST and len(candidate) >= 2:
            return candidate

    return NOT_DETECTED


def extract_document_number(lines: List[str], full_text: str) -> str:
    """
    Extracts document or credential identifier number.
    Supports labels: 'Document Number', 'Document No', 'Doc No', 'Doc Number',
    'ID Number', 'ID No', 'Passport No', 'License No', 'DL No', 'Card No'.
    """
    label_pattern = re.compile(
        r"^(?:document\s*(?:number|no\.?|num|#)|doc\.?\s*(?:number|no\.?|num|#)|"
        r"id\s*(?:number|no\.?|num|#)|identity\s*(?:number|no\.?)|"
        r"passport\s*(?:number|no\.?)|licen[sc]e\s*(?:number|no\.?)|"
        r"dl\s*(?:number|no\.?)|card\s*(?:number|no\.?))\s*[:\-\s]\s*([A-Za-z0-9\-\/]+)",
        re.IGNORECASE
    )
    standalone_label = re.compile(
        r"^(?:document\s*(?:number|no\.?|num|#)|doc\.?\s*(?:number|no\.?|num|#)|"
        r"id\s*(?:number|no\.?|num|#)|identity\s*(?:number|no\.?)|"
        r"passport\s*(?:number|no\.?)|licen[sc]e\s*(?:number|no\.?)|"
        r"dl\s*(?:number|no\.?)|card\s*(?:number|no\.?))\s*[:\-]?$",
        re.IGNORECASE
    )

    for i, line in enumerate(lines):
        line_clean = line.strip()
        match = label_pattern.search(line_clean)
        if match:
            candidate = _clean_str(match.group(1))
            if len(candidate) >= 3:
                return candidate

        # Multi-line match
        if standalone_label.match(line_clean) and i + 1 < len(lines):
            next_line = _clean_str(lines[i + 1])
            if re.match(r"^[A-Za-z0-9\-\/]{3,25}$", next_line):
                return next_line

    # Fallback search across full text
    fallback_match = re.search(
        r"(?:document\s*(?:number|no\.?|num|#)|doc\.?\s*(?:number|no\.?|num|#)|"
        r"id\s*(?:number|no\.?|num|#)|identity\s*(?:number|no\.?)|"
        r"passport\s*(?:number|no\.?))\s*[:\-\s]\s*([A-Za-z0-9\-\/]+)",
        full_text,
        re.IGNORECASE
    )
    if fallback_match:
        candidate = _clean_str(fallback_match.group(1))
        if len(candidate) >= 3:
            return candidate

    return NOT_DETECTED


def extract_nationality(lines: List[str], full_text: str) -> str:
    """
    Extracts nationality or citizenship code / name.
    Supports labels: 'Nationality', 'Citizenship', 'Country', 'Nation'.
    """
    label_pattern = re.compile(
        r"^(?:nationality|citizenship|country\s*of\s*citizenship|country|nation)\s*[:\-\s]\s*([A-Za-z\s]+)$",
        re.IGNORECASE
    )
    standalone_label = re.compile(
        r"^(?:nationality|citizenship|country|nation)\s*[:\-]?$",
        re.IGNORECASE
    )

    for i, line in enumerate(lines):
        line_clean = line.strip()
        match = label_pattern.match(line_clean)
        if match:
            candidate = _clean_str(match.group(1))
            if len(candidate) >= 2:
                return candidate

        if standalone_label.match(line_clean) and i + 1 < len(lines):
            next_line = _clean_str(lines[i + 1])
            if re.match(r"^[A-Za-z\s]{2,30}$", next_line):
                return next_line

    # Fallback across full text
    fallback_match = re.search(
        r"(?:nationality|citizenship|country)\s*[:\-\s]\s*([A-Za-z]{2,20})",
        full_text,
        re.IGNORECASE
    )
    if fallback_match:
        candidate = _clean_str(fallback_match.group(1))
        if len(candidate) >= 2:
            return candidate

    return NOT_DETECTED


# Date pattern supporting DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY, DD Mon YYYY, etc.
DATE_REGEX_STR = (
    r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|"
    r"\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}|"
    r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})"
)


def extract_date_of_birth(lines: List[str], full_text: str) -> str:
    """
    Extracts Date of Birth.
    Supports labels: 'Date of Birth', 'Birth Date', 'DOB', 'D.O.B.', 'Born'.
    """
    label_pattern = re.compile(
        r"^(?:date\s*of\s*birth|birth\s*date|dob|d\.o\.b\.?|born)\s*[:\-\s]\s*" + DATE_REGEX_STR,
        re.IGNORECASE
    )
    standalone_label = re.compile(
        r"^(?:date\s*of\s*birth|birth\s*date|dob|d\.o\.b\.?|born)\s*[:\-]?$",
        re.IGNORECASE
    )

    for i, line in enumerate(lines):
        line_clean = line.strip()
        match = label_pattern.search(line_clean)
        if match:
            return _clean_str(match.group(1))

        if standalone_label.match(line_clean) and i + 1 < len(lines):
            date_match = re.search(DATE_REGEX_STR, lines[i + 1])
            if date_match:
                return _clean_str(date_match.group(1))

    # Fallback across full text
    fallback = re.search(
        r"(?:date\s*of\s*birth|birth\s*date|dob|d\.o\.b\.?|born)\s*[:\-\s]*" + DATE_REGEX_STR,
        full_text,
        re.IGNORECASE
    )
    if fallback:
        return _clean_str(fallback.group(1))

    return NOT_DETECTED


def extract_gender(lines: List[str], full_text: str) -> str:
    """
    Extracts gender or sex.
    Supports labels: 'Gender', 'Sex'.
    Values: M, F, Male, Female, Other, Non-Binary, Transgender.
    """
    gender_val_pattern = r"(Male|Female|Non-Binary|Transgender|Other|\bM\b|\bF\b|\bO\b|\bT\b)"
    label_pattern = re.compile(
        r"^(?:gender|sex)\s*[:\-\s]\s*" + gender_val_pattern,
        re.IGNORECASE
    )
    standalone_label = re.compile(
        r"^(?:gender|sex)\s*[:\-]?$",
        re.IGNORECASE
    )

    for i, line in enumerate(lines):
        line_clean = line.strip()
        match = label_pattern.search(line_clean)
        if match:
            candidate = _clean_str(match.group(1))
            # Format single letter cleanly uppercase, or words title case
            return candidate.upper() if len(candidate) == 1 else candidate.title()

        if standalone_label.match(line_clean) and i + 1 < len(lines):
            val_match = re.search(r"^" + gender_val_pattern + r"$", lines[i + 1].strip(), re.IGNORECASE)
            if val_match:
                cand = _clean_str(val_match.group(1))
                return cand.upper() if len(cand) == 1 else cand.title()

    # Fallback across full text
    fallback = re.search(
        r"(?:gender|sex)\s*[:\-\s]*" + gender_val_pattern,
        full_text,
        re.IGNORECASE
    )
    if fallback:
        cand = _clean_str(fallback.group(1))
        return cand.upper() if len(cand) == 1 else cand.title()

    return NOT_DETECTED


def extract_date_of_issue(lines: List[str], full_text: str) -> str:
    """
    Extracts Date of Issue.
    Supports labels: 'Date of Issue', 'Issue Date', 'Issued on', 'Date Issued', 'DOI', 'D.O.I.'.
    """
    label_pattern = re.compile(
        r"^(?:date\s*of\s*issue|issue\s*date|issued\s*on|date\s*issued|doi|d\.o\.i\.?)\s*[:\-\s]\s*" + DATE_REGEX_STR,
        re.IGNORECASE
    )
    standalone_label = re.compile(
        r"^(?:date\s*of\s*issue|issue\s*date|issued\s*on|date\s*issued|doi|d\.o\.i\.?)\s*[:\-]?$",
        re.IGNORECASE
    )

    for i, line in enumerate(lines):
        line_clean = line.strip()
        match = label_pattern.search(line_clean)
        if match:
            return _clean_str(match.group(1))

        if standalone_label.match(line_clean) and i + 1 < len(lines):
            date_match = re.search(DATE_REGEX_STR, lines[i + 1])
            if date_match:
                return _clean_str(date_match.group(1))

    # Fallback across full text
    fallback = re.search(
        r"(?:date\s*of\s*issue|issue\s*date|issued\s*on|date\s*issued|doi|d\.o\.i\.?)\s*[:\-\s]*" + DATE_REGEX_STR,
        full_text,
        re.IGNORECASE
    )
    if fallback:
        return _clean_str(fallback.group(1))

    return NOT_DETECTED


def extract_date_of_expiry(lines: List[str], full_text: str) -> str:
    """
    Extracts Date of Expiry.
    Supports labels: 'Date of Expiry', 'Date of Expiration', 'Expiry Date',
    'Expiration Date', 'Exp Date', 'Valid Till', 'Valid Until', 'Valid Upto', 'DOE', 'D.O.E.'.
    """
    label_pattern = re.compile(
        r"^(?:date\s*of\s*expiry|date\s*of\s*expiration|expiry\s*date|expiration\s*date|"
        r"exp(?:iry)?\.?\s*date|valid\s*(?:till|until|upto|to)|expires|doe|d\.o\.e\.?)\s*[:\-\s]\s*" + DATE_REGEX_STR,
        re.IGNORECASE
    )
    standalone_label = re.compile(
        r"^(?:date\s*of\s*expiry|date\s*of\s*expiration|expiry\s*date|expiration\s*date|"
        r"exp(?:iry)?\.?\s*date|valid\s*(?:till|until|upto|to)|expires|doe|d\.o\.e\.?)\s*[:\-]?$",
        re.IGNORECASE
    )

    for i, line in enumerate(lines):
        line_clean = line.strip()
        match = label_pattern.search(line_clean)
        if match:
            return _clean_str(match.group(1))

        if standalone_label.match(line_clean) and i + 1 < len(lines):
            date_match = re.search(DATE_REGEX_STR, lines[i + 1])
            if date_match:
                return _clean_str(date_match.group(1))

    # Fallback across full text
    fallback = re.search(
        r"(?:date\s*of\s*expiry|date\s*of\s*expiration|expiry\s*date|expiration\s*date|"
        r"exp(?:iry)?\.?\s*date|valid\s*(?:till|until|upto|to)|expires|doe|d\.o\.e\.?)\s*[:\-\s]*" + DATE_REGEX_STR,
        full_text,
        re.IGNORECASE
    )
    if fallback:
        return _clean_str(fallback.group(1))

    return NOT_DETECTED


def extract_document_fields(ocr_input: Union[Dict[str, Any], str, List[Any]]) -> Dict[str, Any]:
    """
    Main entry point for extracting structured fields from OCR output.

    Args:
        ocr_input: Dict from `extract_document_text`, raw OCR string, or list of line dicts/strings.

    Returns:
        Dict containing:
        - "table_rows": List[Dict[str, str]] with keys "Field" and "Extracted Value"
        - "fields": Dict[str, str] mapping field names to values
        - "detected_count": int (number of fields successfully extracted)
        - "total_fields": int (total number of expected fields, currently 7)
    """
    lines: List[str] = []
    full_text = ""

    # Normalize input formats safely
    if isinstance(ocr_input, dict):
        full_text = str(ocr_input.get("full_text", "") or "")
        raw_lines = ocr_input.get("lines", [])
        for item in raw_lines:
            if isinstance(item, dict):
                txt = item.get("text", "")
                if txt:
                    lines.append(str(txt))
            elif isinstance(item, str) and item:
                lines.append(item)
    elif isinstance(ocr_input, str):
        full_text = ocr_input
        lines = [line.strip() for line in ocr_input.splitlines() if line.strip()]
    elif isinstance(ocr_input, list):
        for item in ocr_input:
            if isinstance(item, dict):
                txt = item.get("text", "")
                if txt:
                    lines.append(str(txt))
            elif isinstance(item, str) and item:
                lines.append(item)
        full_text = "\n".join(lines)

    # If full_text is empty but lines exist, rebuild full_text
    if not full_text and lines:
        full_text = "\n".join(lines)
    # If lines is empty but full_text exists, split lines
    if not lines and full_text:
        lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]

    # Extract each target field
    field_map: Dict[str, str] = {
        "Full Name": extract_full_name(lines, full_text),
        "Document Number": extract_document_number(lines, full_text),
        "Nationality": extract_nationality(lines, full_text),
        "Date of Birth": extract_date_of_birth(lines, full_text),
        "Gender": extract_gender(lines, full_text),
        "Date of Issue": extract_date_of_issue(lines, full_text),
        "Date of Expiry": extract_date_of_expiry(lines, full_text),
    }

    # Build ordered rows for two-column table display
    table_rows: List[Dict[str, str]] = []
    detected_count = 0

    for field_name in FIELD_ORDER:
        val = field_map.get(field_name, NOT_DETECTED)
        if val != NOT_DETECTED:
            detected_count += 1
        table_rows.append({
            "Field": field_name,
            "Extracted Value": val
        })

    return {
        "table_rows": table_rows,
        "fields": field_map,
        "detected_count": detected_count,
        "total_fields": len(FIELD_ORDER)
    }
