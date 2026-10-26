"""
Unit and Integration Tests for Face Detection & Portrait Extraction Service.
Smart India Hackathon (SIH) Problem Statement: SIH26188
"""

import unittest
import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.abspath("."))
from services.face_service import detect_faces, OPENCV_AVAILABLE


class TestFaceDetectionService(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.no_face_path = "data/test_synthetic_document.png"
        cls.single_face_path = "data/test_synthetic_id_with_face.png"
        cls.multi_face_path = "data/test_synthetic_multi_face.png"

        # Verify test files exist
        assert os.path.exists(cls.no_face_path), f"Missing {cls.no_face_path}"
        assert os.path.exists(cls.single_face_path), f"Missing {cls.single_face_path}"
        assert os.path.exists(cls.multi_face_path), f"Missing {cls.multi_face_path}"

    def test_opencv_available(self):
        """OpenCV must be available in the environment."""
        self.assertTrue(OPENCV_AVAILABLE, "OpenCV is required for face detection.")

    def test_detect_zero_faces(self):
        """Document with text only and no photo should detect 0 faces without error."""
        img = Image.open(self.no_face_path)
        res = detect_faces(img)

        self.assertTrue(res["success"], f"Detection failed: {res.get('error')}")
        self.assertEqual(res["face_count"], 0)
        self.assertEqual(len(res["faces"]), 0)
        self.assertIsNotNone(res["annotated_image"])
        self.assertIsNone(res["error"])

    def test_detect_single_face(self):
        """Document with one fictional portrait should detect exactly 1 face."""
        img = Image.open(self.single_face_path)
        res = detect_faces(img)

        self.assertTrue(res["success"], f"Detection failed: {res.get('error')}")
        self.assertEqual(res["face_count"], 1, f"Expected 1 face, found {res['face_count']}")
        self.assertEqual(len(res["faces"]), 1)

        face = res["faces"][0]
        self.assertEqual(face["index"], 1)
        self.assertEqual(len(face["box"]), 4)  # (x, y, w, h)
        self.assertGreater(face["width"], 30)
        self.assertGreater(face["height"], 30)

        # Check cropped portrait
        crop = face["cropped_image"]
        self.assertIsInstance(crop, Image.Image)
        self.assertGreater(crop.width, 0)
        self.assertGreater(crop.height, 0)

    def test_detect_multiple_faces(self):
        """Document with multiple fictional portraits should detect multiple faces."""
        img = Image.open(self.multi_face_path)
        res = detect_faces(img)

        self.assertTrue(res["success"], f"Detection failed: {res.get('error')}")
        self.assertGreaterEqual(res["face_count"], 2, f"Expected >= 2 faces, found {res['face_count']}")
        self.assertGreaterEqual(len(res["faces"]), 2)

        for idx, f in enumerate(res["faces"], start=1):
            self.assertEqual(f["index"], idx)
            self.assertIsInstance(f["cropped_image"], Image.Image)
            self.assertGreater(f["width"], 0)
            self.assertGreater(f["height"], 0)

    def test_preserves_original_image(self):
        """Input image must remain completely unmodified when annotated copy is drawn."""
        img = Image.open(self.single_face_path)
        orig_bytes = np.array(img).tobytes()

        res = detect_faces(img)
        self.assertTrue(res["success"])

        # Check original image bytes are unchanged
        current_bytes = np.array(img).tobytes()
        self.assertEqual(orig_bytes, current_bytes, "Original image was mutated!")

        # Check annotated image is a distinct object
        annotated = res["annotated_image"]
        self.assertIsNot(annotated, img)

    def test_invalid_input_handling(self):
        """Passing None or empty input should return a clean error without crashing."""
        res_none = detect_faces(None)
        self.assertFalse(res_none["success"])
        self.assertEqual(res_none["face_count"], 0)
        self.assertIsNotNone(res_none["error"])

    def test_blank_canvas_image(self):
        """A plain solid color image should gracefully return 0 faces."""
        blank = Image.new("RGB", (300, 300), color=(128, 128, 128))
        res = detect_faces(blank)
        self.assertTrue(res["success"])
        self.assertEqual(res["face_count"], 0)
        self.assertEqual(len(res["faces"]), 0)


if __name__ == "__main__":
    unittest.main()
