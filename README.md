# AI-Based Fake Identity & Document Screening System

**Smart India Hackathon (SIH) Problem Statement:** SIH26188

---

## 📌 Project Objective

The objective of this project is to build an automated, AI-driven verification system capable of screening identity and travel documents (such as passports, driving licenses, national identity cards) for authenticity risks. The system aims to assist border control, law enforcement, and identity verification authorities in detecting fraudulent, forged, or altered identity credentials with high reliability and auditability.

---

## 🏗️ Planned Modules (Roadmap)

The project is structured to be developed incrementally across the following core modules:

1. **Document Ingestion & Image Inspection (`Step 1`)** - *Completed*
   - Secure uploading of JPG, JPEG, and PNG document images.
   - Image format validation, dimension checks, file integrity, and UI reset.

2. **OCR Extraction (`Step 2 - a. OCR Extraction`)** - *Completed*
   - Extract raw text lines and machine-readable text using PaddleOCR.
   - Display full extracted text, line-by-line breakdowns, and recognition confidence scores.
   - *Note: OCR extracts visible characters for downstream parsing. It does NOT prove document authenticity.*

3. **Structured Field Extraction (`Step 2 - b. Field Extraction`)** - *Completed*
   - Parse key identity fields from OCR text:
     - **Full Name**
     - **Document Number**
     - **Nationality**
     - **Date of Birth**
     - **Gender**
     - **Date of Issue**
     - **Date of Expiry**
   - Clean, two-column tabular presentation (`Field` and `Extracted Value`).
   - Strict fallback to `"Not detected"` for any missing or unidentifiable field (no guessing or synthetic hallucinations).
   - Keeps the complete raw OCR recognition stream visible below the structured table for auditing.
   - *Note: Field extraction organizes text for inspection. It does NOT prove authenticity.*

4. **Face Detection & Portrait Extraction (`Step 3 - Face Detection`)** - *Active*
   - OpenCV-based Haar Cascade facial detector (primary frontal cascade + alt2 high-recall fallback with IoU deduplication).
   - Non-destructive processing: draws bounding boxes on a copy of the uploaded document while preserving original upload.
   - Counts and localizes detected facial regions with precise pixel coordinates and bounding boxes.
   - Cropped portrait extraction preview for single and multi-face documents.
   - Helpful guidance when no face is detected without application crashes.
   - *Note: Face detection localizes visual facial regions. It does NOT identify individuals or certify document authenticity.*

5. **Document Validation (`c. Document Validation`)** - *Upcoming*
   - Cross-check checksums and check-digits (e.g., ICAO 9303 standards for passports).
   - Verify layout patterns, alignment, typography, and standard field syntax.

6. **Tampering Detection (`d. Tampering Detection`)** - *Upcoming*
   - Analyze image manipulation artifacts (copy-move forgery, splicing, font irregularities, edge inconsistencies).
   - Inspect digital compression inconsistencies (ELA - Error Level Analysis).

7. **Biometric Face Verification (`e. Biometric Verification`)** - *Upcoming*
   - Compare extracted photo ID portraits against live selfie or reference images with liveness detection.
   - Detect digital re-placement, morphing, and synthetic facial anomalies.

8. **Risk Scoring (`f. Risk Scoring`)** - *Upcoming*
   - Aggregate signals from OCR, validity checks, tampering signals, and biometric matching into a normalized risk score (e.g., Low, Medium, High Risk).

9. **Investigation / Audit Trail (`g. Investigation/Audit Trail`)** - *Upcoming*
   - Generate explainable forensic reports detailing flagged issues.
   - Provide an audit trail for compliance and human review.

---

## 🚦 Current Status

- **Status:** **Active (Document Ingestion, PaddleOCR Text Extraction & Structured Field Extraction)**
- **Active Features:**
  - Clean Streamlit web interface with SIH-themed sidebar and navigation.
  - Document image upload supporting JPG, JPEG, and PNG.
  - Image integrity verification, dimensions, file size, and dynamic preview.
  - Fast, cached PaddleOCR model initialization (`@st.cache_resource`).
  - On-demand **"📄 Extract Text & Parse Fields"** action button.
  - **Structured Document Fields Table:** Dedicated two-column table displaying 7 canonical identity fields.
  - **Zero-Hallucination Fallback:** Any field not found defaults strictly to `"Not detected"`.
  - **Raw Text Transparency:** Complete transcribed text (with `.txt` download) and line-by-line breakdown table with confidence percentages are preserved directly below the structured field table.
  - Helpful error handling for invalid/corrupted files or blank/unreadable images.
- **Important Note:** AI tampering detection, face biometric verification, and fraud/authenticity scoring are not yet active and will be integrated incrementally in subsequent steps.

---

## 📁 Project Directory Structure

```text
AI-Fake-Identity-Screening/
│
├── app.py                         # Main Streamlit application entry point
├── requirements.txt               # Dependencies (Streamlit, PaddleOCR, Pillow, OpenCV)
├── README.md                      # Project documentation and roadmap
├── .gitignore                     # Git ignore rules for Python environment & temporary files
│
├── services/                      # Modular processing logic and detection workflows
│   ├── __init__.py                # Package exports (extract_document_text, extract_document_fields, detect_faces)
│   ├── ocr_service.py             # PaddleOCR extraction service and result parser
│   ├── extraction_service.py      # Structured identity field extraction service
│   └── face_service.py            # OpenCV face detection and portrait extraction service
│
├── models/                        # Model definitions, architectures, and schemas
│   └── __init__.py
│
├── utils/                         # Helper utilities (image processing, helpers)
│   └── __init__.py
│
├── data/                          # Synthetic and test document datasets
│   ├── test_synthetic_document.png# Fictional text-only test ID (0 faces)
│   ├── test_synthetic_id_with_face.png # Fictional synthetic ID card with portrait (1 face)
│   ├── test_synthetic_multi_face.png   # Fictional multi-subject test ID card (2 faces)
│   └── fictional_sample_portrait.jpg   # Fictional synthetic portrait asset
│
├── tests/                         # Automated unit and integration tests
│   ├── test_extraction.py         # Unit tests for field extraction regex and logic
│   ├── test_face_detection.py     # Unit tests for OpenCV face detection & portrait cropping
│   ├── test_ocr_run.py            # Synthetic document generator and OCR runner
│   └── test_synthetic_pipeline.py # End-to-end OCR + field extraction + face detection pipeline test
│
└── docs/                          # Documentation and research specifications
    └── .gitkeep
```

---

## ⚙️ Getting Started & Installation

### 1. Prerequisites
- Python 3.9 – 3.12 installed on your system.
  - *Note on Python 3.12 compatibility:* Use `paddlepaddle>=3.0.0` and `paddleocr>=3.0.0`, which provide official support for Python 3.12.

### 2. Create and Activate Virtual Environment (Recommended)

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**On macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

If installing OCR packages individually:
```bash
pip install paddlepaddle>=3.0.0 paddleocr>=3.0.0
```

### 4. Run the Streamlit Application
```bash
streamlit run app.py
```

Once executed, open your browser at the local URL (typically `http://localhost:8501`).

---

## 🧪 Testing the Feature

### Automated Unit and Pipeline Tests

Run the test suite from your terminal:

```bash
# 1. Run unit tests for face detection service (0 faces, 1 face, multiple faces, immutability)
python -m unittest tests/test_face_detection.py

# 2. Run unit tests for field extraction logic and label variations
python -m unittest tests/test_extraction.py

# 3. Run end-to-end OCR + field extraction + face detection pipeline test
python tests/test_synthetic_pipeline.py

# Or discover and run all tests simultaneously:
python -m unittest discover -s tests -p "test_*.py"
```

### Manual Testing in the Streamlit UI

1. **Launch the Web App:**
   ```bash
   streamlit run app.py
   ```

2. **Test Single Face Detection (Normal Scenario):**
   - Upload `data/test_synthetic_id_with_face.png`.
   - Scroll to **"👤 Face Detection & Portrait Extraction"**.
   - Click **"👤 Detect Faces & Extract Portrait"**.
   - Verify that:
     - Detected Face Count is **1**.
     - An annotated copy with a cyan bounding box and label tag is displayed.
     - A cropped portrait preview is cleanly extracted and displayed on the right.
     - The original uploaded document preview remains completely untouched.

3. **Test Zero Face Detection (Text-Only / Back-Side ID):**
   - Upload `data/test_synthetic_document.png`.
   - Click **"👤 Detect Faces & Extract Portrait"**.
   - Verify that the app displays a helpful warning message ("⚠️ No Face Detected") without crashing.

4. **Test Multiple Face Detection (Multi-Subject ID):**
   - Upload `data/test_synthetic_multi_face.png`.
   - Click **"👤 Detect Faces & Extract Portrait"**.
   - Verify that the count displays **2 faces**, with bounding boxes for all faces and previews for each detected portrait.

5. **Test Reset / Clear:**
   - Click **"🔄 Clear / Reset Upload"** to ensure all session states (OCR, fields, face detection) reset cleanly.
