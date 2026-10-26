"""
End-to-End Pipeline Verification Test
Verifies PaddleOCR extraction + structured field extraction on the synthetic test document.
"""

import sys
import os
from PIL import Image

sys.path.insert(0, os.path.abspath("."))
from services.ocr_service import extract_document_text
from services.extraction_service import extract_document_fields, NOT_DETECTED

from services.face_service import detect_faces

def test_pipeline():
    image_path = "data/test_synthetic_document.png"
    if not os.path.exists(image_path):
        from tests.test_ocr_run import create_synthetic_doc
        create_synthetic_doc(image_path)

    img = Image.open(image_path)
    ocr_result = extract_document_text(img)
    assert ocr_result["success"] is True, f"OCR failed: {ocr_result.get('error')}"

    extracted = extract_document_fields(ocr_result)
    fields = extracted["fields"]

    print("Pipeline Output Table:")
    for row in extracted["table_rows"]:
        print(f"  {row['Field']:<16} : {row['Extracted Value']}")

    assert fields["Full Name"] == "ARUN KUMAR", f"Expected ARUN KUMAR, got {fields['Full Name']}"
    assert fields["Document Number"] == "TEST12345", f"Expected TEST12345, got {fields['Document Number']}"
    assert fields["Nationality"] == "IND", f"Expected IND, got {fields['Nationality']}"
    assert fields["Date of Birth"] == "14/07/2002", f"Expected 14/07/2002, got {fields['Date of Birth']}"
    assert fields["Gender"] == "M", f"Expected M, got {fields['Gender']}"
    assert fields["Date of Issue"] == NOT_DETECTED, f"Expected {NOT_DETECTED}, got {fields['Date of Issue']}"
    assert fields["Date of Expiry"] == "14/07/2032", f"Expected 14/07/2032, got {fields['Date of Expiry']}"

    print("\nSUCCESS: All structured fields accurately match the synthetic document!")

def test_pipeline_with_face():
    image_path = "data/test_synthetic_id_with_face.png"
    if not os.path.exists(image_path):
        print("Note: synthetic id with face not found, skipping face verification.")
        return

    img = Image.open(image_path)
    face_res = detect_faces(img)
    assert face_res["success"] is True, f"Face detection failed: {face_res.get('error')}"
    assert face_res["face_count"] == 1, f"Expected 1 face, found {face_res['face_count']}"
    assert len(face_res["faces"]) == 1
    assert face_res["faces"][0]["cropped_image"] is not None
    print(f"SUCCESS: Face detection localized portrait at box {face_res['faces'][0]['box']} with crop size {face_res['faces'][0]['cropped_image'].size}!")

if __name__ == "__main__":
    test_pipeline()
    test_pipeline_with_face()
