# VeriDoc AI: AI-Based Fake Identity & Document Screening System

SIH 2026 project · Problem Statement **SIH26188**

## Problem Description

Identity and supporting documents can be altered, expired, or inconsistent. Reviewers need a repeatable way to surface document signals and understand why a case needs closer review.

## Solution

VeriDoc AI is a local Python and Streamlit MVP. It accepts a document image or PDF, estimates its type from text, extracts labeled fields, validates basic formats and dates, compares extracted fields with a fictional SQLite registry, measures possible image-manipulation indicators, optionally compares a face when a reference image and InsightFace runtime are available, and calculates a deterministic score with reasons. The UI has separate Upload, Verifying, and Result screens.

**The MVP uses simulated trusted reference data and does not connect to real government or institutional databases.** A registry miss is a limited review signal, not proof that a document is fake.

On the current Windows workspace, PaddleOCR 2.10 is installed but this machine's Application Control blocks a native DLL during engine import, and no Tesseract executable is available. For the exact bundled file `sample_data/genuine/veridoc_demo_certificate.png`, the app uses a clearly labeled Demo OCR Fallback with predefined fictional fields. It pixel-matches that asset and does not activate on unknown, edited, or re-compressed documents. Other files show the actual OCR-unavailable error and are not assigned fabricated text.

## Features

- PNG, JPG/JPEG, WEBP, TIFF, and PDF upload
- Document type keyword classification with an explicit confidence estimate
- PaddleOCR text/box/confidence extraction when an installed engine works, with Tesseract binding/CLI fallback when present
- Exact-match Demo OCR Fallback for the bundled fictional CERT001 certificate only
- Explicit `OCR unavailable` result when neither engine is available; no text is fabricated
- Conservative document-specific extraction and format/date validation
- Basic TD3 passport MRZ check-digit checks when two complete MRZ lines are visible
- Trusted demo comparison for document number, name, date of birth, nationality, gender, expiry, register number, CGPA, and institution
- Pillow/NumPy ELA-style recompression and local noise indicators; these are review signals, not proof of forgery
- Optional InsightFace embedding similarity when installed and a fictional reference face is configured
- Explainable 0-100 risk score and SQLite screening history
- Manual OCR transcript fallback in the pipeline API for development and tests

## Current Status

Working local MVP. PaddleOCR/Tesseract are used when installed and allowed by the operating environment; otherwise the exact bundled fictional certificate can use Demo OCR Fallback. Other documents remain marked OCR unavailable. Face matching is optional. No identity decision is guaranteed; human review remains necessary.

## Architecture

```text
Streamlit upload
	-> image/PDF preparation
	-> keyword type estimate
	-> PaddleOCR / Tesseract / exact synthetic-demo fallback / explicit unavailable status
	-> field extraction
	-> trusted SQLite lookup and document validation
	-> MRZ / image-forensics / optional face checks
	-> explainable risk score
	-> result screen and screening_history audit row
```

See [docs/architecture.md](docs/architecture.md), [docs/methodology.md](docs/methodology.md), and [docs/dataset.md](docs/dataset.md).

## Technology Stack

- Python 3.11 recommended
- Streamlit
- SQLite
- Pillow and NumPy
- PyMuPDF for PDF page rendering
- pytest
- Optional OCR: PaddleOCR/PaddlePaddle or Tesseract (not installed by base requirements)
- Optional: InsightFace, ONNX Runtime, and OpenCV for face comparison

Pandas is not directly listed or imported by VeriDoc AI. The app avoids Streamlit dataframe APIs; a normal Streamlit installation may still install pandas as a transitive dependency for those APIs.

## Dataset and Mock Database

`data/trusted_registry.db` is initialized by `database.py` and contains fictional examples such as `CERT001 / ARUN KUMAR / 21CS001 / CGPA 9.0` and `P0001 / RAHUL SHARMA`. No reference face images are included by default, so face verification reports `NOT_AVAILABLE`. Store only synthetic test files in `sample_data/`.

## Installation

From the project root in PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The base requirements intentionally exclude OCR engines because PaddleOCR installs native dependencies such as `scikit-image` that may be blocked by device policy. If your device administrator approves them, install PaddleOCR/PaddlePaddle using the official Windows instructions for your Python version. Alternatively, install Tesseract on the system PATH (or its Python binding plus the executable). At startup the app tries PaddleOCR, then an already-available Tesseract engine; if neither works it reports the exact error and does not invent text. For optional face matching, separately install compatible `insightface`, `onnxruntime`, and `opencv-python-headless` builds; these are intentionally not default dependencies.

## How to Run

```powershell
python -m streamlit run app.py
```

Open the local URL printed by Streamlit. For PDF uploads, PyMuPDF renders the first page. OCR returns `full_text`, `lines`, average `confidence`, `engine`, and `error` alongside compatibility metadata. A missing or unreadable OCR engine is reported in the results; the Result screen can accept a manual transcript for synthetic demos, which is labeled as manual and is not represented as OCR output.

To exercise Demo OCR Fallback in this Windows environment, upload `sample_data/genuine/veridoc_demo_certificate.png` unchanged. It must pixel-match this bundled fictional fixture; a modified or re-compressed image is treated as an unknown document and does not receive predefined text.

## How to Test

```powershell
python -m pytest -q
```

Tests use temporary SQLite files and synthetic images/transcripts; they do not require real documents or face data.

## Limitations

- Keyword document classification is a heuristic, not a trained classifier.
- Labeled regex extraction depends on readable OCR labels and may miss varied layouts.
- MRZ support checks two-line TD3 passports only; it does not establish passport authenticity.
- ELA/noise differences can arise from benign compression, scanning, or camera capture.
- Face similarity is an optional heuristic; it can be wrong and is not a standalone identity decision.
- The demo registry contains only a few fictional records and is not authoritative.
- OCR quality depends on scan quality and downloaded language models.

## Privacy and Security Notes

Use synthetic documents only. Uploaded content is processed locally by this MVP and is not intentionally persisted; the SQLite audit log stores the filename, extracted document number, score, status, and reasons, so do not use real identity details. Restrict access to the local machine and clear demo history before sharing a database file. No real government or university data/API is used. A production deployment would need consent, encryption, access control, retention rules, human review, and separately authorised API agreements.

## Future Enhancements

- Robust document layout detection and better extraction for additional formats
- Additional MRZ formats and signed-document checks
- Calibrated image-forensics signals evaluated on a consented synthetic dataset
- Secure, authorised reference API integration where legally approved
- Role-based reviewer workflow, retention controls, and downloadable audit reports

## Team Contribution

Add project-team names, responsibilities, and contributions here before submission.
