"""
AI-Based Fake Identity & Document Screening System
Smart India Hackathon (SIH) Problem Statement: SIH26188

Module 1: Document Ingestion & Upload Management
Module 2: OCR Text Extraction (Powered by PaddleOCR)
Module 3: Structured Document Field Extraction
Module 4: Face Detection & Portrait Extraction (Powered by OpenCV)

Note: OCR and face detection localize document contents and features.
They do NOT prove document authenticity or indicate whether an identity document is genuine.
"""

import streamlit as st
from PIL import Image, UnidentifiedImageError

from services.ocr_service import (
    extract_document_text,
    PADDLE_AVAILABLE,
)
from services.extraction_service import (
    extract_document_fields,
    NOT_DETECTED,
    FIELD_ORDER,
)
from services.face_service import (
    detect_faces,
    OPENCV_AVAILABLE,
)

# --- Page Configuration ---
st.set_page_config(
    page_title="Fake Identity & Document Screening (SIH26188)",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State Initialization ---
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

if "ocr_result" not in st.session_state:
    st.session_state["ocr_result"] = None

if "extracted_fields" not in st.session_state:
    st.session_state["extracted_fields"] = None

if "face_result" not in st.session_state:
    st.session_state["face_result"] = None

if "last_processed_filename" not in st.session_state:
    st.session_state["last_processed_filename"] = None

def reset_uploader():
    """Increment key to reset the file uploader and clear stored pipeline results."""
    st.session_state["uploader_key"] += 1
    st.session_state["ocr_result"] = None
    st.session_state["extracted_fields"] = None
    st.session_state["face_result"] = None
    st.session_state["last_processed_filename"] = None


# --- Sidebar Navigation & SIH Project Details ---
with st.sidebar:
    st.markdown("## 🛡️ SIH Portal")
    st.caption("AI-Based Fake Identity & Document Screening")

    st.markdown("---")
    st.markdown("### 📋 Problem Statement Details")
    st.markdown(
        """
        - **Problem ID:** `SIH26188`
        - **Domain:** Artificial Intelligence / Security
        - **Category:** Software / Forensics
        - **Active Stages:** Ingestion, OCR, Field Extraction, Face Detection
        """
    )

    st.markdown("---")
    st.markdown("### 📌 Document Guidelines")
    st.markdown(
        """
        - **Supported Formats:** JPG, JPEG, PNG
        - **Target Documents:** Passports, National IDs, Driving Licenses, PAN, Voter ID
        - **Best Practices:**
          - Ensure all four corners are visible
          - Avoid intense flash reflections or glare
          - Ensure text and photo areas are crisp and legible
        """
    )

    st.markdown("---")
    st.markdown("### 🗺️ Screening Pipeline Roadmap")
    st.markdown(
        """
        - 🟢 **Step 1: Document Upload & Inspection** *(Active)*
        - 🟢 **Step 2: OCR Text Extraction** *(Active - PaddleOCR)*
        - 🟢 **Step 3: Structured Field Extraction** *(Active - 7 Core Fields)*
        - 🟢 **Step 4: Face Detection & Portrait Extraction** *(Active - OpenCV)*
        - ⚪ **Step 5: Tampering & Forgery Detection** *(Upcoming)*
        - ⚪ **Step 6: Facial Biometric Verification** *(Upcoming)*
        - ⚪ **Step 7: Composite Risk Scoring** *(Upcoming)*
        """
    )

    st.markdown("---")
    st.caption("SIH 2024 / Screening Pipeline Baseline v1.2")


# --- Main Content Area ---
st.title("🛡️ AI-Based Fake Identity & Document Screening System")
st.markdown(
    "**Smart India Hackathon (SIH26188)** | Automated document verification, tampering detection, and identity assurance platform."
)

st.markdown(
    """
    This screening portal ingests official identity and travel documents to inspect authenticity, 
    detect digital alterations, and verify credential integrity. 
    Upload a document image and extract its textual contents using the modules below.
    """
)

st.divider()

# --- Module Header & Upload Controls ---
header_col, action_col = st.columns([3, 1])

with header_col:
    st.subheader("📄 Document Ingestion Module")
    st.caption("Upload a scanned copy or clear photograph of the identity document for screening.")

with action_col:
    # Button to clear / reset current upload
    st.write("")  # Spacing alignment
    if st.button("🔄 Clear / Reset Upload", use_container_width=True, help="Click to clear the current upload and reset the form"):
        reset_uploader()
        st.rerun()

# --- File Uploader Widget ---
uploaded_file = st.file_uploader(
    label="Upload document image (JPG, JPEG, PNG)",
    type=["jpg", "jpeg", "png"],
    key=f"document_uploader_{st.session_state['uploader_key']}",
    help="Select or drag-and-drop a document image in JPG, JPEG, or PNG format."
)

# --- Upload Processing & Validation ---
if uploaded_file is not None:
    # If the user uploaded a new/different file, reset previous pipeline results
    if st.session_state.get("last_processed_filename") != uploaded_file.name:
        st.session_state["ocr_result"] = None
        st.session_state["extracted_fields"] = None
        st.session_state["face_result"] = None
        st.session_state["last_processed_filename"] = uploaded_file.name

    try:
        # Validate that the file is a readable and non-corrupted image
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image.load()  # Force load image data to detect file corruption or truncation
        
        width, height = image.size
        img_format = image.format or uploaded_file.type.split("/")[-1].upper()
        color_mode = image.mode
        file_size_bytes = uploaded_file.size
        
        # Format file size for human readability
        if file_size_bytes >= 1024 * 1024:
            file_size_display = f"{file_size_bytes / (1024 * 1024):.2f} MB"
        else:
            file_size_display = f"{file_size_bytes / 1024:.2f} KB"

        st.success(f"✅ **Document Loaded Successfully:** `{uploaded_file.name}` has been validated.")

        # Layout: Left column for Document Preview, Right column for Document Metadata
        col_preview, col_meta = st.columns([3, 2], gap="large")

        with col_preview:
            st.markdown("#### 🖼️ Document Preview")
            st.image(
                image,
                caption=f"Uploaded File: {uploaded_file.name}",
                use_container_width=True
            )

        with col_meta:
            st.markdown("#### 📊 Document Information & Properties")
            
            # Key metrics displayed in clean cards
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                st.metric(label="Width", value=f"{width} px")
                st.metric(label="File Format", value=str(img_format))
            with m_col2:
                st.metric(label="Height", value=f"{height} px")
                st.metric(label="File Size", value=file_size_display)

            st.markdown("---")
            st.markdown("**Extended Properties:**")
            st.markdown(
                f"""
                - **Original Filename:** `{uploaded_file.name}`
                - **Resolution:** `{width} × {height}` pixels ({width * height:,} total pixels)
                - **Aspect Ratio:** `{width / height:.2f}:1`
                - **Color Mode:** `{color_mode}`
                - **Ingestion Status:** `Verified & Ready for OCR`
                """
            )

        # =========================================================================
        # --- Module 2: OCR Text Extraction Section ---
        # =========================================================================
        st.divider()
        st.subheader("🔍 OCR Text Extraction")
        st.caption("Extract printed and machine-readable text lines from the document using PaddleOCR.")

        # Disclaimer required for SIH hackathon evaluation
        st.info(
            "ℹ️ **Evaluation Disclaimer:** OCR text extraction retrieves legible text characters "
            "for automated field inspection. **Extracted text does not certify that the document is genuine.** "
            "Tampering checks and authenticity scoring will be handled in subsequent pipeline stages."
        )

        if not PADDLE_AVAILABLE:
            st.warning(
                "⚠️ PaddleOCR library is not detected in your Python environment. "
                "Please run `pip install paddlepaddle>=3.0.0 paddleocr>=3.0.0` to enable text extraction."
            )
        else:
            # Action button to trigger OCR and field extraction
            col_btn, _ = st.columns([2, 3])
            with col_btn:
                run_ocr_button = st.button(
                    "📄 Extract Text & Parse Fields",
                    type="primary",
                    use_container_width=True,
                    help="Click to initiate optical character recognition and field parsing on this document"
                )

            if run_ocr_button:
                with st.spinner("Extracting text and identifying document fields... (PaddleOCR engine cached)"):
                    ocr_res = extract_document_text(image)
                    st.session_state["ocr_result"] = ocr_res
                    if ocr_res.get("success"):
                        st.session_state["extracted_fields"] = extract_document_fields(ocr_res)
                    else:
                        st.session_state["extracted_fields"] = None

            # Display OCR results and structured fields if available in session state
            current_ocr = st.session_state.get("ocr_result")
            if current_ocr is not None:
                if current_ocr.get("success"):
                    line_count = current_ocr.get("line_count", 0)
                    avg_conf = current_ocr.get("avg_confidence", 0.0)
                    lines = current_ocr.get("lines", [])
                    full_text = current_ocr.get("full_text", "")

                    # Retrieve or compute structured fields
                    current_fields = st.session_state.get("extracted_fields")
                    if current_fields is None:
                        current_fields = extract_document_fields(current_ocr)
                        st.session_state["extracted_fields"] = current_fields

                    if line_count > 0:
                        st.success(
                            f"✅ **Extraction & Parsing Complete:** Successfully recognized **{line_count}** text segment(s) "
                            f"with an average confidence of **{avg_conf * 100:.1f}%**."
                        )

                        # Display Summary Metrics
                        met_c1, met_c2, met_c3 = st.columns(3)
                        with met_c1:
                            st.metric("Total Lines Extracted", value=line_count)
                        with met_c2:
                            st.metric("Mean Recognition Confidence", value=f"{avg_conf * 100:.1f}%")
                        with met_c3:
                            st.metric(
                                "Identified Fields",
                                value=f"{current_fields['detected_count']} / {current_fields['total_fields']}"
                            )

                        # -----------------------------------------------------------------
                        # 1. Structured Document Fields Table
                        # -----------------------------------------------------------------
                        st.markdown("---")
                        st.markdown("### 📋 Structured Document Fields")
                        st.caption(
                            "Parsed credential fields recognized from the document. "
                            "Unidentifiable fields default strictly to `Not detected`."
                        )

                        # Evaluation Disclaimer (Requirement 10)
                        st.info(
                            "ℹ️ **Document Screening Disclaimer:** Structured field extraction parses recognized OCR text into key identity fields. "
                            "**Extracted fields do NOT prove or certify document authenticity.** "
                            "Forensic tampering detection and biometric checks are evaluated in subsequent pipeline stages."
                        )

                        # Two-column table: Field and Extracted Value (Requirement 4)
                        table_rows = current_fields.get("table_rows", [])
                        st.dataframe(
                            table_rows,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Field": st.column_config.TextColumn(
                                    "Field",
                                    help="Standard document field name",
                                    width="medium"
                                ),
                                "Extracted Value": st.column_config.TextColumn(
                                    "Extracted Value",
                                    help="Value recognized by OCR or 'Not detected'",
                                    width="large"
                                )
                            }
                        )

                        # -----------------------------------------------------------------
                        # 2. Raw OCR Recognition Results (Requirement 6)
                        # Complete raw OCR text visible below the extracted fields
                        # -----------------------------------------------------------------
                        st.markdown("---")
                        st.markdown("### 📝 Raw OCR Recognition Results")
                        st.caption(
                            "Original unparsed text lines and character recognition confidence scores directly from PaddleOCR."
                        )

                        tab_full, tab_breakdown = st.tabs(["📄 Full Transcribed Text", "📑 Line-by-Line Breakdown"])

                        with tab_full:
                            st.text_area(
                                label="Full Extracted Document Text",
                                value=full_text,
                                height=200,
                                help="Copy or inspect the raw transcribed text content"
                            )
                            st.download_button(
                                label="💾 Download Raw Text (.txt)",
                                data=full_text,
                                file_name=f"{uploaded_file.name}_raw_ocr.txt",
                                mime="text/plain"
                            )

                        with tab_breakdown:
                            st.markdown("##### Detailed Text Segments with Confidence Scores")
                            table_data = [
                                {
                                    "Line #": idx + 1,
                                    "Recognized Text": item["text"],
                                    "Confidence": f"{item['confidence'] * 100:.2f}%"
                                }
                                for idx, item in enumerate(lines)
                            ]
                            st.dataframe(
                                table_data,
                                use_container_width=True,
                                hide_index=True
                            )
                    else:
                        # No text detected in the document
                        st.warning(
                            "⚠️ **No Text Detected:** The OCR engine did not find any legible text segments in this image.\n\n"
                            "**Suggestions:**\n"
                            "- Ensure the document image has sufficient contrast and lighting.\n"
                            "- Check if the document is oriented right-side up.\n"
                            "- Ensure the resolution is clear enough for character recognition."
                        )
                        st.markdown("---")
                        st.markdown("### 📋 Structured Document Fields")
                        empty_fields = extract_document_fields("")
                        st.dataframe(
                            empty_fields["table_rows"],
                            use_container_width=True,
                            hide_index=True
                        )
                else:
                    # OCR error handled gracefully without crashing the app
                    st.error(
                        f"❌ **OCR Extraction Failed:** {current_ocr.get('error', 'Unknown OCR error')}\n\n"
                        "Please verify your image and try again."
                    )

        # =========================================================================
        # --- Module 4: Face Detection & Portrait Extraction Section ---
        # =========================================================================
        st.divider()
        st.subheader("👤 Face Detection & Portrait Extraction")
        st.caption("Localize facial biometric regions and extract cropped portrait previews using OpenCV.")

        # SIH Evaluation Disclaimer (Requirement 10)
        st.info(
            "ℹ️ **Evaluation Disclaimer:** Face detection localizes facial regions and extracts portrait bounding boxes "
            "from the document image. **Face detection does NOT authenticate identity, verify personhood, or certify document genuineness.** "
            "Biometric comparison and tampering forensics are evaluated in subsequent pipeline stages."
        )

        if not OPENCV_AVAILABLE:
            st.warning(
                "⚠️ OpenCV library is not detected in your Python environment. "
                "Please run `pip install opencv-python>=4.8.0` to enable face detection."
            )
        else:
            # Action button to trigger face detection (Requirement 3)
            col_face_btn, _ = st.columns([2, 3])
            with col_face_btn:
                run_face_btn = st.button(
                    "👤 Detect Faces & Extract Portrait",
                    type="primary",
                    key="btn_run_face_detection",
                    use_container_width=True,
                    help="Click to initiate OpenCV face detection and extract portrait previews from this document"
                )

            if run_face_btn:
                with st.spinner("Analyzing document image for facial features (OpenCV Haar detector)..."):
                    face_res = detect_faces(image)
                    st.session_state["face_result"] = face_res

            # Display Face Detection results if available in session state
            current_face = st.session_state.get("face_result")
            if current_face is not None:
                if current_face.get("success"):
                    face_count = current_face.get("face_count", 0)
                    faces = current_face.get("faces", [])
                    annotated_img = current_face.get("annotated_image")

                    if face_count == 0:
                        # Helpful message when no face is detected without crashing (Requirement 7)
                        st.warning(
                            "⚠️ **No Face Detected:** The detector did not find any facial regions in this document image.\n\n"
                            "**Suggestions:**\n"
                            "- Ensure the document contains a clear, unobstructed photograph.\n"
                            "- Check if the document is oriented right-side up.\n"
                            "- Verify that lighting and contrast are sufficient for facial feature localization."
                        )
                        st.metric(label="Detected Face Count", value=0)

                    elif face_count == 1:
                        # Single face detected (Requirement 6)
                        st.success(
                            "✅ **Single Face Detected:** Exactly **1** portrait region was successfully localized."
                        )
                        face = faces[0]
                        box_x, box_y, box_w, box_h = face["box"]
                        crop_img = face["cropped_image"]

                        # Display detected face count and dimensions (Requirement 4)
                        m1, m2, m3 = st.columns(3)
                        with m1:
                            st.metric(label="Detected Face Count", value=1)
                        with m2:
                            st.metric(label="Face Bounding Box", value=f"{box_w} × {box_h} px")
                        with m3:
                            st.metric(label="Box Location (X, Y)", value=f"({box_x}, {box_y})")

                        # Previews: Annotated Document on left, Cropped Portrait on right (Requirements 5 & 6)
                        col_ann, col_crop = st.columns([3, 2], gap="large")
                        with col_ann:
                            st.markdown("#### 🖼️ Document with Face Bounding Box")
                            st.caption("Annotated copy showing localized face coordinates. Original upload is preserved.")
                            st.image(
                                annotated_img,
                                caption=f"Document with Face Detection Overlay ({uploaded_file.name})",
                                use_container_width=True
                            )

                        with col_crop:
                            st.markdown("#### 👤 Cropped Portrait Preview")
                            st.caption("Extracted portrait photograph bounded from the document.")
                            st.image(
                                crop_img,
                                caption=f"Extracted Portrait ({crop_img.width} × {crop_img.height} px)",
                                width=220
                            )
                            st.markdown(
                                f"""
                                - **Bounding Box:** `x={box_x}, y={box_y}, w={box_w}, h={box_h}`
                                - **Extracted Size:** `{crop_img.width} × {crop_img.height}` pixels
                                - **Status:** `Portrait Extracted & Ready for Inspection`
                                """
                            )

                    else:
                        # Multiple faces detected (Requirement 8)
                        st.warning(
                            f"⚠️ **Multiple Faces Detected:** Detected **{face_count}** facial regions in this document image.\n\n"
                            "Standard ID documents typically contain a single primary photograph. Multiple faces may indicate a group photo, a secondary thumbnail/ghost image, or background artifacts."
                        )

                        m1, m2 = st.columns(2)
                        with m1:
                            st.metric(label="Detected Face Count", value=face_count)
                        with m2:
                            st.caption("Review extracted portraits below to verify the primary credential subject.")

                        col_ann, col_crops = st.columns([3, 2], gap="large")
                        with col_ann:
                            st.markdown("#### 🖼️ Document with All Detected Faces")
                            st.caption("Annotated copy with bounding boxes for all detected faces.")
                            st.image(
                                annotated_img,
                                caption=f"Document with {face_count} Detected Faces",
                                use_container_width=True
                            )

                        with col_crops:
                            st.markdown("#### 👥 Detected Portrait Previews")
                            st.caption(f"Previews for all {face_count} detected regions:")
                            for f in faces:
                                idx = f["index"]
                                bx, by, bw, bh = f["box"]
                                cimg = f["cropped_image"]
                                st.markdown(f"**Face #{idx}** (`{bw} × {bh}` px at `({bx}, {by})`)")
                                st.image(cimg, width=180)
                                st.divider()

                else:
                    st.error(
                        f"❌ **Face Detection Failed:** {current_face.get('error', 'Unknown face detection error')}\n\n"
                        "Please verify your image and try again."
                    )

        # Informational Callout regarding upcoming AI screening pipeline stages
        st.markdown("---")
        with st.expander("🚀 Next Screening Pipeline Modules (Upcoming)", expanded=False):
            st.markdown(
                """
                The following AI screening stages will process this document in upcoming implementation steps:
                1. **Structured Field Validation:** Cross-referencing parsed fields (Name, DOB, ID number) against checksums.
                2. **Tampering & Forgery Analysis:** Error Level Analysis (ELA), copy-move detection, and font consistency verification.
                3. **Biometric Face Verification:** Face extraction and similarity cross-matching.
                4. **Risk Scoring Engine:** Weighted fraud likelihood score and actionable audit report.
                """
            )

    except (UnidentifiedImageError, OSError, SyntaxError) as err:
        st.error(
            f"❌ **Invalid or Corrupted Image**: The file `{uploaded_file.name}` could not be decoded as a valid image. "
            f"Please ensure it is an uncorrupted JPG, JPEG, or PNG file.\n\n"
            f"*Technical details:* `{err}`"
        )
    except Exception as general_err:
        st.error(
            f"❌ **Unexpected Error**: Failed to process `{uploaded_file.name}`. "
            f"Please try again or upload a different file.\n\n"
            f"*Error message:* `{general_err}`"
        )

else:
    # Empty State: Friendly instructions when no file has been uploaded
    st.info(
        "👆 **Get Started:** Drag and drop an identity document image above, or click **Browse files** to upload "
        "a JPG, JPEG, or PNG document (e.g., Aadhaar card, PAN card, Passport, or Driver's License)."
    )
    
    # Feature overview card for SIH demo audience
    with st.container():
        st.markdown("### 💡 Document Screening Pipeline Overview")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("##### 1. Secure Ingestion")
            st.caption("Validates file integrity, dimensions, format, and memory layout.")
        with c2:
            st.markdown("##### 2. PaddleOCR Extraction")
            st.caption("Transcribes printed and machine-readable text lines with confidence scores.")
        with c3:
            st.markdown("##### 3. Forensic Analysis")
            st.caption("Prepares the raw pixel array for downstream tampering and fraud detection.")
