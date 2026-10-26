# Architecture

## Local MVP flow

1. Streamlit receives an image or PDF upload and keeps its bytes in session state.
2. `services.pipeline.run_screening` opens the file, applies EXIF orientation, resizes it, and renders the first PDF page with PyMuPDF.
3. `document_detector` estimates a type from OCR keywords and the filename. It returns `UNKNOWN` when evidence is absent or tied.
4. `ocr.extract_text` lazily initializes PaddleOCR and returns `full_text`, `lines`, average confidence, engine, and error. If PaddleOCR cannot initialize or run, an installed Tesseract binding/CLI is attempted. Only when neither engine is available does the service compare exact normalized pixels against the bundled fictional certificate; an exact match returns predefined fields with engine `Demo OCR Fallback`. Every other image remains OCR-unavailable with empty text. Tests/manual development may pass a transcript directly to the pipeline.
5. `field_extractor` reads labeled values. `validation` applies per-type required fields, format/date rules, and registry status/mismatch checks.
6. `database.compare_with_trusted` looks up a fictional demo record by document number and compares available values. Missing reference data is an unavailable match, not a fraud verdict.
7. `mrz_validator` checks two-line TD3 MRZ structure/check digits when present. `tampering` measures image recompression and local noise variation. `face_verification` optionally compares InsightFace embeddings only when the record includes a usable reference face.
8. `risk_score` sums deterministic weighted factors, caps the score at 100, and returns factor points and reasons.
9. The Result screen shows outputs and `database.save_screening_result` writes a local audit row.

## Modules

- `app.py`: the three-screen Streamlit flow, progress callbacks, and result rendering.
- `config.py`: local paths and upload limits.
- `database.py`: idempotent schema initialization, fictional registry lookup/comparison, and history.
- `services/`: isolated detection, OCR, extraction, validation, MRZ, forensics, optional face, scoring, and pipeline code.
- `data/trusted_registry.db`: local SQLite demo registry and screening history.

## Trust boundary

The SQLite registry contains fictional data only. No government, university, police, or real identity service is contacted. Production integrations require explicit legal authorization, security review, consent, and access controls.
