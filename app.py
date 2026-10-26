import streamlit as st

from config import ALLOWED_UPLOAD_TYPES, MAX_UPLOAD_SIZE_MB
from database import get_screening_history
from services.pipeline import PIPELINE_STEPS, run_screening


st.set_page_config(
    page_title="VeriDoc AI | SIH 2026",
    page_icon="V",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');

    :root {
        --ink: #172b45;
        --muted: #687b91;
        --blue: #2878dc;
        --blue-dark: #1d63bd;
        --blue-soft: #edf5ff;
        --line: #d9e6f4;
        --canvas: #f5f8fc;
        --green: #13845b;
        --amber: #a96812;
        --red: #b63b45;
    }

    html, body, [class*="st-"] {
        font-family: 'DM Sans', 'Segoe UI', sans-serif;
        color: var(--ink);
    }
    .stApp {
        background: linear-gradient(180deg, #f8fbff 0%, var(--canvas) 100%);
        color: var(--ink);
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stToolbar"] { right: 1rem; }
    .block-container { max-width: 1000px; padding: 2rem 1.5rem 4rem; }

    .brand {
        display: flex;
        align-items: center;
        gap: 12px;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid var(--line);
    }
    .brand-mark {
        display: grid;
        width: 42px;
        height: 42px;
        place-items: center;
        border-radius: 12px;
        background: var(--blue);
        box-shadow: 0 5px 14px rgba(40, 120, 220, 0.2);
        color: white;
        font-family: 'Manrope', sans-serif;
        font-size: 20px;
        font-weight: 800;
    }
    .brand-name {
        color: var(--ink);
        font-family: 'Manrope', sans-serif;
        font-size: 19px;
        font-weight: 800;
        line-height: 1.25;
    }
    .brand-subtitle { margin-top: 3px; color: var(--muted); font-size: 12px; }

    .stepper {
        display: flex;
        justify-content: center;
        gap: 12px;
        margin: 1.8rem 0 2.2rem;
        color: #8b9bad;
        font-size: 12px;
    }
    .step-item { display: flex; align-items: center; gap: 7px; }
    .step-number {
        display: grid;
        width: 24px;
        height: 24px;
        place-items: center;
        border: 1px solid #d6e1ee;
        border-radius: 50%;
        background: white;
        font-size: 11px;
    }
    .step-item.active { color: var(--blue-dark); font-weight: 700; }
    .step-item.active .step-number { border-color: var(--blue); background: var(--blue); color: white; }
    .step-connector { width: 28px; height: 1px; margin: auto 0; background: var(--line); }

    .page-title {
        margin: 0 0 8px;
        color: var(--ink);
        font-family: 'Manrope', sans-serif;
        font-size: 30px;
        font-weight: 800;
        letter-spacing: 0;
        line-height: 1.2;
        text-align: center;
    }
    .page-copy { margin: 0 auto 1.5rem; color: var(--muted); font-size: 14px; text-align: center; }
    .upload-card, .result-card, .verify-card {
        padding: clamp(18px, 4vw, 34px);
        border: 1px solid var(--line);
        border-radius: 14px;
        background: white;
        box-shadow: 0 12px 34px rgba(30, 66, 105, 0.07);
    }
    .upload-icon {
        display: grid;
        width: 58px;
        height: 58px;
        margin: 0 auto 14px;
        place-items: center;
        border: 1px solid #d4e6fc;
        border-radius: 16px;
        background: var(--blue-soft);
        color: var(--blue);
        font-size: 26px;
    }
    .card-heading { margin: 0 0 6px; color: var(--ink); font-size: 16px; font-weight: 700; text-align: center; }
    .card-copy { margin: 0 0 18px; color: var(--muted); font-size: 13px; text-align: center; }
    .supported {
        margin: 15px 0 0;
        color: var(--muted);
        font-size: 12px;
        text-align: center;
    }
    div[data-testid="stFileUploader"] section {
        border: 1px dashed #a9c7e8;
        border-radius: 10px;
        background: #f8fbff;
    }
    div[data-testid="stFileUploader"] section:hover { border-color: var(--blue); }
    div[data-testid="stFileUploader"] section small { color: var(--muted); }
    div[data-testid="stImage"] img { border: 1px solid var(--line); border-radius: 9px; }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--line);
        border-radius: 12px;
        background: white;
    }
    div.stButton > button {
        min-height: 44px;
        border: 1px solid var(--line);
        border-radius: 8px;
        color: var(--ink);
        font-weight: 700;
    }
    div.stButton > button[kind="primary"] {
        border-color: var(--blue);
        background: var(--blue);
        color: white;
    }
    div.stButton > button[kind="primary"]:hover { border-color: var(--blue-dark); background: var(--blue-dark); }
    div.stButton > button[kind="secondary"] {
        border-color: #bfd5ee;
        background: #edf5ff;
        color: var(--blue-dark);
    }
    div.stButton > button[kind="secondary"]:hover {
        border-color: #8cb6e5;
        background: #e1efff;
        color: #174f94;
    }

    .file-label {
        margin: 16px 0 8px;
        color: var(--muted);
        font-size: 11px;
        font-weight: 700;
        text-align: center;
        text-transform: uppercase;
    }
    .file-name {
        overflow-wrap: anywhere;
        color: var(--ink);
        font-size: 13px;
        font-weight: 600;
        text-align: center;
    }
    .pdf-preview {
        display: grid;
        min-height: 140px;
        place-items: center;
        border: 1px solid var(--line);
        border-radius: 9px;
        background: #f8fbff;
        color: var(--blue-dark);
        font-size: 14px;
        font-weight: 700;
    }
    .demo-note {
        margin-top: 16px;
        color: #77889c;
        font-size: 11px;
        line-height: 1.6;
        text-align: center;
    }
    .verification-layout { display: grid; grid-template-columns: minmax(180px, 0.8fr) 1.2fr; gap: 26px; align-items: start; }
    .steps-list { display: grid; gap: 13px; margin-top: 18px; }
    .verification-step { display: flex; align-items: center; gap: 12px; color: #8898aa; font-size: 13px; }
    .verification-step.active { color: var(--blue-dark); font-weight: 700; }
    .verification-step.done { color: var(--green); }
    .step-dot {
        display: grid;
        flex: 0 0 27px;
        width: 27px;
        height: 27px;
        place-items: center;
        border: 1px solid #dbe5f0;
        border-radius: 50%;
        background: white;
        font-size: 11px;
    }
    .verification-step.active .step-dot { border-color: #9cc5f2; background: var(--blue-soft); color: var(--blue); }
    .verification-step.done .step-dot { border-color: #bce5d4; background: #edf9f3; }
    .result-label { color: var(--muted); font-size: 12px; font-weight: 700; text-align: center; text-transform: uppercase; }
    .score { margin: 8px 0 3px; color: var(--ink); font-family: 'Manrope', sans-serif; font-size: 58px; font-weight: 800; line-height: 1; text-align: center; }
    .score span { color: #8a9aad; font-size: 19px; font-weight: 600; }
    .risk-badge {
        width: fit-content;
        margin: 14px auto 0;
        padding: 7px 13px;
        border: 1px solid #f1d4ad;
        border-radius: 20px;
        background: #fff8ed;
        color: var(--amber);
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.04em;
    }
    .risk-badge.low { border-color: #bce5d4; background: #edf9f3; color: var(--green); }
    .risk-badge.medium, .risk-badge.review { border-color: #f1dfc6; background: #fffbf5; color: var(--amber); }
    .risk-badge.high { border-color: #f0c8cc; background: #fff5f5; color: var(--red); }
    .reason-list { display: grid; gap: 9px; margin-top: 14px; }
    .reason {
        display: flex;
        gap: 9px;
        padding: 11px 12px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #fbfdff;
        color: #42546a;
        font-size: 13px;
    }
    .reason.warning { border-color: #f1dfc6; background: #fffbf5; }
    .reason.pass { border-color: #d4ebdf; background: #f7fcf9; }
    .indicator-row { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin: 15px 0; }
    .indicator {
        padding: 5px 9px;
        border: 1px solid var(--line);
        border-radius: 20px;
        color: var(--muted);
        font-size: 10px;
        font-weight: 700;
    }
    .indicator.warning { border-color: #f1dfc6; background: #fffbf5; color: var(--amber); }
    .indicator.pass { border-color: #d4ebdf; background: #f7fcf9; color: var(--green); }
    .details-box { padding: 15px; border: 1px solid var(--line); border-radius: 9px; background: #f8fbff; color: var(--muted); font-size: 12px; line-height: 1.7; }

    @media (max-width: 640px) {
        .block-container { padding: 1.1rem 1rem 2rem; }
        .brand { align-items: flex-start; }
        .brand-subtitle { max-width: 290px; line-height: 1.45; }
        .stepper { gap: 6px; margin: 1.4rem 0 1.8rem; font-size: 10px; }
        .step-connector { width: 12px; }
        .page-title { font-size: 25px; }
        .verification-layout { grid-template-columns: 1fr; }
        .score { font-size: 50px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_header(active_stage):
    stage_names = [("upload", "Upload", "1"), ("verifying", "Verify", "2"), ("result", "Result", "3")]
    stepper_parts = []
    for stage, label, number in stage_names:
        active_class = " active" if active_stage == stage else ""
        stepper_parts.append(
            f'<div class="step-item{active_class}"><div class="step-number">{number}</div>{label}</div>'
        )
    stepper_html = '<div class="stepper">' + '<div class="step-connector"></div>'.join(stepper_parts) + '</div>'

    st.markdown(
        """
        <div class="brand">
            <div class="brand-mark">V</div>
            <div>
                <div class="brand-name">VeriDoc AI</div>
                <div class="brand-subtitle">AI-Based Fake Identity &amp; Document Screening System</div>
            </div>
        </div>
        """ + stepper_html,
        unsafe_allow_html=True,
    )


def render_file_preview(uploaded_file):
    if uploaded_file.type == "application/pdf":
        st.markdown(
            f'<div class="pdf-preview">PDF document<br><small>{uploaded_file.name}</small></div>',
            unsafe_allow_html=True,
        )
    else:
        st.image(uploaded_file, caption=uploaded_file.name, width="stretch")


def render_upload_screen():
    render_header("upload")
    st.markdown('<h1 class="page-title">Upload your document</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-copy">Start a new document screening session.</p>', unsafe_allow_html=True)

    left, center, right = st.columns([1, 2.5, 1])
    with center:
        with st.container(border=True):
            st.markdown('<div class="upload-icon">↑</div>', unsafe_allow_html=True)
            st.markdown('<div class="card-heading">Choose a document to screen</div>', unsafe_allow_html=True)
            st.markdown('<p class="card-copy">Drag and drop your file here, or browse to upload</p>', unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "Upload document",
                type=ALLOWED_UPLOAD_TYPES,
                label_visibility="collapsed",
                key="document_upload",
                max_upload_size=MAX_UPLOAD_SIZE_MB,
            )
            st.markdown(
                '<p class="supported">Passport &bull; ID &bull; Visa &bull; Certificate &bull; Permit</p><p class="supported">PNG &bull; JPG &bull; JPEG &bull; WEBP &bull; TIFF &bull; PDF</p>',
                unsafe_allow_html=True,
            )

            if uploaded_file is not None:
                st.markdown('<div class="file-label">Selected document preview</div>', unsafe_allow_html=True)
                if uploaded_file.type == "application/pdf":
                    render_file_preview(uploaded_file)
                else:
                    st.image(uploaded_file, caption=uploaded_file.name, width="stretch")
                st.session_state.uploaded_file = uploaded_file

            st.write("")
            if st.button(
                "VERIFY DOCUMENT",
                type="primary",
                use_container_width=True,
                disabled=uploaded_file is None,
                key="start_verification",
            ):
                st.session_state.uploaded_file = uploaded_file
                st.session_state.screen = "verifying"
                st.rerun()

    st.markdown(
        '<div class="demo-note">UI prototype only. Document verification is simulated and does not connect to real identity registries.</div>',
        unsafe_allow_html=True,
    )


def render_verification_steps(active_index):
    rows = []
    for index, label in enumerate(PIPELINE_STEPS):
        state = "done" if index < active_index else "active" if index == active_index else ""
        marker = "&#10003;" if index < active_index else str(index + 1)
        rows.append(
            f'<div class="verification-step {state}"><div class="step-dot">{marker}</div><span>{label}</span></div>'
        )
    return '<div class="steps-list">' + "".join(rows) + "</div>"


def render_verifying_screen():
    render_header("verifying")
    st.markdown('<h1 class="page-title">Verifying Document</h1>', unsafe_allow_html=True)
    st.markdown('<p class="page-copy">Please wait while the screening steps run.</p>', unsafe_allow_html=True)

    uploaded_file = st.session_state.get("uploaded_file")
    if uploaded_file is None:
        st.warning("No document is selected. Return to upload and choose a file.")
        if st.button("Back to upload", type="primary"):
            st.session_state.screen = "upload"
            st.rerun()
        return

    preview_column, progress_column = st.columns([0.8, 1.2], gap="large")
    with preview_column:
        with st.container(border=True):
            st.markdown('<div class="card-heading">Uploaded document</div>', unsafe_allow_html=True)
            render_file_preview(uploaded_file)
    with progress_column:
        with st.container(border=True):
            st.markdown('<div class="card-heading">Screening progress</div>', unsafe_allow_html=True)
            step_statuses = ["pending"] * len(PIPELINE_STEPS)
            progress = st.progress(0, text="Preparing screening...")
            steps_placeholder = st.empty()

            def update_progress(event):
                index = event["index"]
                step_statuses[index] = event["status"]
                completed = sum(status in {"complete", "warning"} for status in step_statuses)
                value = completed / len(PIPELINE_STEPS)
                if event["status"] == "running":
                    value = (index + 0.2) / len(PIPELINE_STEPS)
                progress.progress(
                    min(1.0, value),
                    text=f"{event['label']} · {event['status'].replace('_', ' ').title()}",
                )
                active_index = next(
                    (position for position, status in enumerate(step_statuses) if status == "running"),
                    min(completed, len(PIPELINE_STEPS) - 1),
                )
                steps_placeholder.markdown(
                    render_verification_steps(active_index),
                    unsafe_allow_html=True,
                )

            screening = run_screening(
                uploaded_file.getvalue(),
                uploaded_file.name,
                on_step=update_progress,
            )

    st.session_state.screening_result = screening
    st.session_state.screen = "result"
    st.rerun()


def render_rows(headers, rows):
    if not rows:
        return
    keys = [key for _, key in headers]
    with st.container(border=True):
        header_columns = st.columns(len(headers))
        for column, (label, _) in zip(header_columns, headers):
            column.markdown(f"**{label}**")
        for row in rows:
            value_columns = st.columns(len(headers))
            for column, key in zip(value_columns, keys):
                value = row.get(key, "")
                column.write("" if value is None else str(value))


def render_result_screen():
    render_header("result")
    st.markdown('<h1 class="page-title">Screening Result</h1>', unsafe_allow_html=True)
    screening = st.session_state.get("screening_result")
    if not screening:
        st.warning("No screening result is available. Upload a document to begin.")
        if st.button("Back to upload", type="primary"):
            st.session_state.screen = "upload"
            st.rerun()
        return

    uploaded_file = st.session_state.get("uploaded_file")
    risk = screening.get("risk", {})
    risk_level = risk.get("risk_level", "REVIEW REQUIRED")
    risk_class = {
        "LOW RISK": "low",
        "MEDIUM RISK": "medium",
        "REVIEW REQUIRED": "review",
        "HIGH RISK": "high",
    }.get(risk_level, "review")
    score = int(risk.get("score", 0))
    st.markdown(
        f'<p class="page-copy">{screening.get("final_status", "Review the checks below.")}</p>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown('<div class="result-label">Risk Score</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="score">{score} <span>/ 100</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="risk-badge {risk_class}">{risk_level}</div>', unsafe_allow_html=True)
        st.progress(score / 100)
        st.markdown('<div class="card-heading">Screening reasons</div>', unsafe_allow_html=True)
        for reason in risk.get("reasons", []):
            matched = "matched trusted demo record" in reason.lower()
            icon = "&#10003;" if matched else "&#9888;"
            kind = "pass" if matched else "warning"
            st.markdown(
                f'<div class="reason {kind}"><span>{icon}</span>{reason}</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            '<div class="demo-note">Screening is an aid, not proof of authenticity. The trusted registry contains fictional demo records only; no government or institutional database is connected.</div>',
            unsafe_allow_html=True,
        )

    ocr_result = screening.get("ocr", {})
    ocr_status = ocr_result.get("status")
    if ocr_status == "DEMO":
        st.info(
            f"**OCR Engine: Demo OCR Fallback**\n\n{ocr_result.get('error') or ''}\n\n"
            "The fields below are predefined fictional demo values, not text recognized from the image."
        )
    elif ocr_status == "OK":
        st.success(f"**OCR Engine: {ocr_result.get('engine') or 'OCR'} · Real OCR result**")
    elif ocr_status == "MANUAL":
        st.info("**OCR Mode: Manual transcription** · These values were entered by the reviewer.")

    if ocr_status not in {"OK", "MANUAL", "DEMO"}:
        ocr_error = ocr_result.get("error") or "The OCR engine returned no text."
        st.error(ocr_error)
        with st.container(border=True):
            st.markdown("**Manual transcription (optional)**")
            st.write("Shown only because OCR did not complete. Enter text from a fictional or synthetic document; it will not be labeled as OCR output.")
            with st.form("manual_ocr_fallback"):
                manual_text = st.text_area("Transcribed document text", height=130, key="manual_ocr_text")
                retry_manual = st.form_submit_button("Continue with manual text", type="primary")
            if retry_manual and uploaded_file is not None and manual_text.strip():
                with st.spinner("Re-running checks with the supplied manual transcript..."):
                    screening = run_screening(
                        uploaded_file.getvalue(),
                        uploaded_file.name,
                        manual_text=manual_text,
                    )
                st.session_state.screening_result = screening
                st.rerun()
    if screening.get("history_error"):
        st.warning(screening["history_error"])

    details_column, another_column = st.columns(2, gap="medium")
    with details_column:
        if st.button("VIEW DETAILS", type="secondary", use_container_width=True, disabled=False, key="view_details"):
            st.session_state.show_details = not st.session_state.get("show_details", False)
    with another_column:
        if st.button("SCREEN ANOTHER DOCUMENT", type="secondary", use_container_width=True, key="screen_another"):
            st.session_state.screen = "upload"
            st.session_state.show_details = False
            st.session_state.uploaded_file = None
            st.session_state.screening_result = None
            st.session_state.pop("document_upload", None)
            st.rerun()

    if not st.session_state.get("show_details", False):
        return

    st.markdown('<h3>Screening details</h3>', unsafe_allow_html=True)
    left_column, right_column = st.columns([0.9, 1.1], gap="large")
    with left_column:
        with st.container(border=True):
            st.markdown('<div class="card-heading">Uploaded document</div>', unsafe_allow_html=True)
            if uploaded_file is not None:
                render_file_preview(uploaded_file)
            else:
                st.caption(screening.get("filename", "Document preview unavailable."))
    with right_column:
        with st.container(border=True):
            st.markdown('<div class="card-heading">Document assessment</div>', unsafe_allow_html=True)
            st.write(f"**Detected type:** {screening.get('document_type', 'UNKNOWN')} ({screening.get('document_detection', {}).get('confidence', 0):.0%} confidence)")
            if ocr_status == "DEMO":
                st.write("**OCR Engine:** Demo OCR Fallback · Fictional predefined fields")
            elif ocr_status == "OK":
                st.write(f"**OCR Engine:** {ocr_result.get('engine') or 'OCR'} · Real OCR result")
            elif ocr_status == "MANUAL":
                st.write("**OCR Mode:** Manual transcription")
            else:
                st.write(f"**OCR Engine:** Unavailable · {ocr_status or 'NOT AVAILABLE'}")
            if screening.get("ocr", {}).get("error"):
                st.caption(screening["ocr"]["error"])
            field_rows = [
                {"field": key.replace("_", " ").title(), "value": value}
                for key, value in screening.get("fields", {}).items()
                if value not in (None, "") and key != "document_type"
            ]
            if field_rows:
                render_rows([("Field", "field"), ("Extracted value", "value")], field_rows)
            else:
                st.info("No structured fields were extracted.")

    trusted = screening.get("trusted_match", {})
    st.markdown('<h4>Trusted reference match</h4>', unsafe_allow_html=True)
    if trusted.get("record_found"):
        if trusted.get("mismatched_fields"):
            st.warning(trusted.get("message", "Fields differ from the demo record."))
            mismatch_rows = [
                {"field": key.replace("_", " ").title(), **values}
                for key, values in trusted["mismatched_fields"].items()
            ]
            render_rows(
                [("Field", "field"), ("Extracted", "extracted"), ("Trusted demo", "trusted")],
                mismatch_rows,
            )
        else:
            st.success(trusted.get("message", "Trusted demo record found."))
        st.caption(f"Registry status: {trusted.get('database_status', 'UNKNOWN')} · Matched fields: {', '.join(trusted.get('matched_fields', [])) or 'none'}")
    else:
        st.info(trusted.get("message", "Trusted reference record unavailable."))

    validation = screening.get("validation", {})
    st.markdown('<h4>Document validation</h4>', unsafe_allow_html=True)
    st.write(f"**Status:** {validation.get('status', 'NOT AVAILABLE')}")
    for heading, checks in (
        ("Passed", validation.get("passed_checks", [])),
        ("Failed", validation.get("failed_checks", [])),
        ("Warnings", validation.get("warnings", [])),
    ):
        if checks:
            st.write(f"**{heading}:**")
            for check in checks:
                st.write(f"- {check}")

    mrz = screening.get("mrz", {})
    tampering = screening.get("tampering", {})
    face = screening.get("face", {})
    analysis_column, face_column = st.columns(2, gap="large")
    with analysis_column:
        st.markdown('<h4>MRZ and tampering analysis</h4>', unsafe_allow_html=True)
        st.write(f"**MRZ:** {mrz.get('status', 'NOT_AVAILABLE')} · {mrz.get('message', '')}")
        st.write(f"**Possible manipulation indicators:** {tampering.get('level', 'NOT_AVAILABLE')} · score {tampering.get('tampering_score', 0):.2f}/1")
        st.caption(tampering.get("message", "Tampering analysis unavailable."))
        if tampering.get("suspicious_regions"):
            st.write(f"Regions flagged for review: {len(tampering['suspicious_regions'])}")
    with face_column:
        st.markdown('<h4>Face verification</h4>', unsafe_allow_html=True)
        st.write(f"**Status:** {face.get('status', 'NOT_AVAILABLE')}")
        if face.get("similarity") is not None:
            st.write(f"**Similarity:** {face['similarity']:.3f}")
        st.caption(face.get("reason", "Face verification unavailable."))

    st.markdown('<h4>Risk score breakdown</h4>', unsafe_allow_html=True)
    breakdown_rows = [
        {"factor": key.replace("_", " ").title(), "points": value}
        for key, value in risk.get("breakdown", {}).items()
    ]
    if breakdown_rows:
        render_rows([("Risk factor", "factor"), ("Points", "points")], breakdown_rows)

    history = get_screening_history(limit=5)
    if history:
        st.markdown('<h4>Recent screening history</h4>', unsafe_allow_html=True)
        render_rows(
            [("Time (UTC)", "timestamp"), ("File", "filename"), ("Type", "document_type"), ("Risk", "risk"), ("Status", "final_status")],
            [
                {
                    "timestamp": row["timestamp"],
                    "filename": row["filename"],
                    "document_type": row["document_type"],
                    "risk": f"{row['risk_score']} · {row['risk_level']}",
                    "final_status": row["final_status"],
                }
                for row in history
            ],
        )


if "screen" not in st.session_state:
    st.session_state.screen = "upload"
if "show_details" not in st.session_state:
    st.session_state.show_details = False

if st.session_state.screen == "upload":
    render_upload_screen()
elif st.session_state.screen == "verifying":
    render_verifying_screen()
else:
    render_result_screen()