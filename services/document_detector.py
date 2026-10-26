import re


KEYWORDS = {
    "PASSPORT": ("PASSPORT", "P<"),
    "VISA": ("VISA", "ENTRY PERMIT"),
    "ID_CARD": ("IDENTITY CARD", "ID CARD", "NATIONAL ID", "DRIVING LICENCE", "DRIVER LICENSE"),
    "CERTIFICATE": ("CERTIFICATE", "CGPA", "REGISTER NO", "GRADE POINT", "TRANSCRIPT"),
    "PERMIT": ("WORK PERMIT", "RESIDENCE PERMIT", "PERMIT NO", "PERMIT NUMBER"),
}


def detect_document_type(text, filename=""):
    """Estimate a document type from visible OCR keywords and filename hints."""
    combined = f"{text or ''}\n{filename or ''}".upper()
    scores = {}
    evidence = {}
    for document_type, keywords in KEYWORDS.items():
        found = [keyword for keyword in keywords if keyword in combined]
        if found:
            scores[document_type] = len(found)
            evidence[document_type] = found

    if not scores:
        return {"document_type": "UNKNOWN", "confidence": 0.0, "evidence": []}

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_type, best_score = ranked[0]
    if len(ranked) > 1 and ranked[1][1] == best_score:
        return {"document_type": "UNKNOWN", "confidence": 0.25, "evidence": evidence[best_type]}
    confidence = min(0.96, 0.55 + 0.12 * (best_score - 1))
    return {
        "document_type": best_type,
        "confidence": round(confidence, 2),
        "evidence": evidence[best_type],
    }
