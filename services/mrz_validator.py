import re
from datetime import datetime


MRZ_PATTERN = re.compile(r"^[A-Z0-9<]{28,44}$")


def _check_digit(value):
    weights = (7, 3, 1)
    total = 0
    for index, char in enumerate(value):
        if char == "<":
            number = 0
        elif char.isdigit():
            number = int(char)
        elif "A" <= char <= "Z":
            number = ord(char) - ord("A") + 10
        else:
            return None
        total += number * weights[index % 3]
    return str(total % 10)


def _clean(value):
    return value.replace("<", " ").strip()


def _name_from_mrz(line):
    names = line[5:].split("<<", maxsplit=1)
    surname = _clean(names[0])
    given_names = _clean(names[1]) if len(names) > 1 else ""
    return " ".join(part for part in (given_names, surname) if part).strip()


def _date_to_mrz(value):
    for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(str(value), date_format).strftime("%y%m%d")
        except ValueError:
            continue
    return None


def validate_mrz(text, visible_fields=None):
    """Validate basic TD3 passport MRZ check digits when a two-line MRZ is found."""
    visible_fields = visible_fields or {}
    candidates = [
        re.sub(r"\s+", "", line.upper())
        for line in (text or "").splitlines()
        if MRZ_PATTERN.fullmatch(re.sub(r"\s+", "", line.upper()))
    ]
    td3_lines = [line for line in candidates if len(line) == 44]
    if len(td3_lines) < 2 or not td3_lines[-2].startswith("P<"):
        return {
            "status": "NOT_AVAILABLE",
            "lines": candidates,
            "checks": [],
            "mismatches": [],
            "message": "No complete two-line TD3 passport MRZ was detected.",
            "fields": {},
        }

    line_one, line_two = td3_lines[-2:]
    checks = []
    for label, value, digit in (
        ("passport number", line_two[0:9], line_two[9]),
        ("date of birth", line_two[13:19], line_two[19]),
        ("expiry date", line_two[21:27], line_two[27]),
        ("composite", line_two[0:10] + line_two[13:20] + line_two[21:43], line_two[43]),
    ):
        expected = _check_digit(value)
        checks.append({"name": label, "passed": expected is not None and expected == digit})

    mrz_fields = {
        "document_number": line_two[0:9].replace("<", "").strip(),
        "nationality": line_two[10:13].replace("<", "").strip(),
        "date_of_birth": line_two[13:19],
        "gender": line_two[20],
        "expiry_date": line_two[21:27],
        "name": _name_from_mrz(line_one),
    }
    mismatches = []
    for key in ("document_number", "name", "nationality", "gender"):
        visible = visible_fields.get(key)
        from_mrz = mrz_fields.get(key)
        if visible and from_mrz:
            compact_visible = re.sub(r"[^A-Z0-9]", "", str(visible).upper())
            compact_mrz = re.sub(r"[^A-Z0-9]", "", str(from_mrz).upper())
            if compact_visible != compact_mrz:
                mismatches.append(key)
    for key in ("date_of_birth", "expiry_date"):
        visible = _date_to_mrz(visible_fields.get(key))
        if visible and visible != mrz_fields[key]:
            mismatches.append(key)

    passed = all(check["passed"] for check in checks)
    status = "INCONSISTENT" if not passed or mismatches else "VALID"
    return {
        "status": status,
        "lines": [line_one, line_two],
        "checks": checks,
        "mismatches": mismatches,
        "message": "MRZ check digits passed." if status == "VALID" else "MRZ check digits or visible fields are inconsistent.",
        "fields": mrz_fields,
    }
