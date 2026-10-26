# Synthetic Sample Data

Store only fictional or synthetically generated test files here. Never add real Aadhaar, passport, college, identity, or personal data.

- `genuine/`: optional synthetic originals, such as the fictional `CERT001` certificate.
- `tampered/`: optional copies with deliberately changed synthetic fields or photo regions.

`genuine/veridoc_demo_certificate.png` is the bundled synthetic certificate accepted by Demo OCR Fallback when real OCR engines are unavailable. The fallback compares normalized pixels against that exact asset. Upload the bundled PNG unchanged; a re-scanned, re-compressed, edited, or otherwise different image will not receive predefined OCR text.

The expected demo certificate registry record is fictional: `CERT001`, `ARUN KUMAR`, `21CS001`, `CGPA 9.0`. No face photograph is bundled. Document-type, real OCR, and face checks are best-effort indicators and do not prove authenticity. Demo OCR fallback is predefined sample data, not text recognized from image pixels.

Supported test scenarios include a field-modified synthetic certificate, a synthetic photo-swapped copy, an expired demo status, and a document with no trusted reference record.
