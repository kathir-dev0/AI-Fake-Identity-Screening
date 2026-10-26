"""
Unit tests for structured document field extraction service.
"""

import unittest
from services.extraction_service import (
    extract_document_fields,
    NOT_DETECTED,
    FIELD_ORDER
)


class TestFieldExtraction(unittest.TestCase):

    def test_standard_synthetic_sample(self):
        """Tests the exact synthetic sample from the user requirement."""
        raw_text = (
            "TEST DOCUMENT — NOT VALID FOR IDENTIFICATION\n"
            "Name: ARUN KUMAR\n"
            "Document Number: TEST12345\n"
            "Nationality: IND\n"
            "Date of Birth: 14/07/2002\n"
            "Gender: M\n"
            "Date of Expiry: 14/07/2032"
        )
        res = extract_document_fields(raw_text)
        fields = res["fields"]

        self.assertEqual(fields["Full Name"], "ARUN KUMAR")
        self.assertEqual(fields["Document Number"], "TEST12345")
        self.assertEqual(fields["Nationality"], "IND")
        self.assertEqual(fields["Date of Birth"], "14/07/2002")
        self.assertEqual(fields["Gender"], "M")
        self.assertEqual(fields["Date of Issue"], NOT_DETECTED)
        self.assertEqual(fields["Date of Expiry"], "14/07/2032")
        self.assertEqual(res["detected_count"], 6)
        self.assertEqual(res["total_fields"], 7)

        # Verify table rows format
        table_rows = res["table_rows"]
        self.assertEqual(len(table_rows), 7)
        self.assertIn({"Field": "Full Name", "Extracted Value": "ARUN KUMAR"}, table_rows)
        self.assertIn({"Field": "Date of Issue", "Extracted Value": "Not detected"}, table_rows)

    def test_label_variations(self):
        """Tests variations like DOB, Expiry Date, Document No, Date of Issue, Sex."""
        raw_text = (
            "Full Name: JANE DOE\n"
            "Document No: DL-987654321\n"
            "Citizenship: Canadian\n"
            "DOB: 1995-11-20\n"
            "Sex: Female\n"
            "Date of Issue: 01/01/2020\n"
            "Expiry Date: 01/01/2030\n"
        )
        res = extract_document_fields(raw_text)
        fields = res["fields"]

        self.assertEqual(fields["Full Name"], "JANE DOE")
        self.assertEqual(fields["Document Number"], "DL-987654321")
        self.assertEqual(fields["Nationality"], "Canadian")
        self.assertEqual(fields["Date of Birth"], "1995-11-20")
        self.assertEqual(fields["Gender"], "Female")
        self.assertEqual(fields["Date of Issue"], "01/01/2020")
        self.assertEqual(fields["Date of Expiry"], "01/01/2030")
        self.assertEqual(res["detected_count"], 7)

    def test_multiline_labels_and_values(self):
        """Tests when OCR breaks label and value across lines."""
        lines = [
            "Name:",
            "PRIYA SHARMA",
            "Doc Number",
            "IND992200",
            "Country",
            "IND",
            "Birth Date:",
            "25/08/1998",
            "Gender:",
            "F",
            "Valid Till:",
            "25/08/2028"
        ]
        res = extract_document_fields(lines)
        fields = res["fields"]

        self.assertEqual(fields["Full Name"], "PRIYA SHARMA")
        self.assertEqual(fields["Document Number"], "IND992200")
        self.assertEqual(fields["Nationality"], "IND")
        self.assertEqual(fields["Date of Birth"], "25/08/1998")
        self.assertEqual(fields["Gender"], "F")
        self.assertEqual(fields["Date of Expiry"], "25/08/2028")
        self.assertEqual(fields["Date of Issue"], NOT_DETECTED)

    def test_empty_and_unreadable_text(self):
        """Tests graceful fallback when text is empty or missing."""
        res_empty = extract_document_fields("")
        for row in res_empty["table_rows"]:
            self.assertEqual(row["Extracted Value"], NOT_DETECTED)
        self.assertEqual(res_empty["detected_count"], 0)

        res_garbage = extract_document_fields("Random noise 12345 !@#$%")
        self.assertEqual(res_garbage["fields"]["Full Name"], NOT_DETECTED)
        self.assertEqual(res_garbage["fields"]["Nationality"], NOT_DETECTED)

    def test_no_guessed_values(self):
        """Ensures that missing fields strictly stay 'Not detected'."""
        text = "Name: ALEX CARTER\nGender: M"
        res = extract_document_fields(text)
        self.assertEqual(res["fields"]["Full Name"], "ALEX CARTER")
        self.assertEqual(res["fields"]["Gender"], "M")
        self.assertEqual(res["fields"]["Document Number"], NOT_DETECTED)
        self.assertEqual(res["fields"]["Nationality"], NOT_DETECTED)
        self.assertEqual(res["fields"]["Date of Birth"], NOT_DETECTED)
        self.assertEqual(res["fields"]["Date of Issue"], NOT_DETECTED)
        self.assertEqual(res["fields"]["Date of Expiry"], NOT_DETECTED)


if __name__ == "__main__":
    unittest.main()
