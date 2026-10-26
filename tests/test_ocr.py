from PIL import Image
from types import SimpleNamespace

from services import ocr


class FakePaddleEngine:
    def ocr(self, image, cls=True):
        box = [[0, 0], [120, 0], [120, 20], [0, 20]]
        return [[box, ("CERTIFICATE ID: CERT001", 0.98)]]


class FakePaddleTwoLineEngine:
    def ocr(self, image, cls=True):
        first_box = [[0, 0], [120, 0], [120, 20], [0, 20]]
        second_box = [[0, 24], [120, 24], [120, 44], [0, 44]]
        return [[
            [first_box, ("CERTIFICATE ID: CERT001", 0.98)],
            [second_box, ("NAME: ARUN KUMAR", 0.96)],
        ]]


class FakePaddleV3Result:
    json = {
        "res": {
            "rec_texts": ["NAME: ARUN KUMAR"],
            "rec_scores": [0.97],
            "dt_polys": [[[0, 0], [120, 0], [120, 20], [0, 20]]],
        }
    }


class FakePaddleV3Engine:
    def predict(self, image):
        return [FakePaddleV3Result()]


def test_ocr_returns_text_boxes_and_confidence(monkeypatch):
    monkeypatch.setattr(ocr, "_get_paddle_engine", lambda: FakePaddleEngine())
    result = ocr.extract_text(Image.new("RGB", (160, 80), "white"))
    assert result["status"] == "OK"
    assert "CERTIFICATE ID: CERT001" in result["text"]
    assert result["full_text"] == result["text"]
    assert result["lines"] == ["CERTIFICATE ID: CERT001"]
    assert result["confidence"] == 0.98
    assert result["engine"] == "PaddleOCR"
    assert result["error"] is None
    assert result["boxes"]
    assert result["confidences"] == [0.98]


def test_ocr_parses_both_lines_from_paddle_v2_output(monkeypatch):
    monkeypatch.setattr(ocr, "_get_paddle_engine", lambda: FakePaddleTwoLineEngine())
    result = ocr.extract_text(Image.new("RGB", (160, 80), "white"))
    assert result["text"].splitlines() == ["CERTIFICATE ID: CERT001", "NAME: ARUN KUMAR"]
    assert result["confidences"] == [0.98, 0.96]
    assert result["lines"] == ["CERTIFICATE ID: CERT001", "NAME: ARUN KUMAR"]
    assert result["confidence"] == 0.97


def test_ocr_parses_paddle_v3_result_objects(monkeypatch):
    monkeypatch.setattr(ocr, "_get_paddle_engine", lambda: FakePaddleV3Engine())
    result = ocr.extract_text(Image.new("RGB", (160, 80), "white"))
    assert result["status"] == "OK"
    assert result["text"] == "NAME: ARUN KUMAR"
    assert result["confidences"] == [0.97]


def test_uses_available_tesseract_cli_when_paddle_fails(monkeypatch):
    monkeypatch.setattr(ocr, "_get_paddle_engine", lambda: None)
    monkeypatch.setattr(ocr, "_paddle_error", "Application Control blocked PaddleOCR")
    monkeypatch.setattr(ocr.shutil, "which", lambda _: "tesseract.exe")
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t10\t20\t100\t30\t90\tCERTIFICATE\n"
        "5\t1\t1\t1\t1\t2\t115\t20\t50\t30\t80\tCERT001\n"
    )
    monkeypatch.setattr(
        ocr.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=tsv.encode(), stderr=b""),
    )
    result = ocr.extract_text(Image.new("RGB", (160, 80), "white"))
    assert result["engine"] == "Tesseract"
    assert result["full_text"] == "CERTIFICATE CERT001"
    assert result["lines"] == ["CERTIFICATE CERT001"]
    assert result["confidence"] == 0.85


def test_no_working_engine_returns_clear_unavailable_result(monkeypatch):
    monkeypatch.setattr(ocr, "_get_paddle_engine", lambda: None)
    monkeypatch.setattr(ocr, "_paddle_error", "Application Control blocked PaddleOCR")
    monkeypatch.setattr(ocr.shutil, "which", lambda _: None)
    result = ocr.extract_text(Image.new("RGB", (160, 80), "white"))
    assert result["status"] == "UNAVAILABLE"
    assert result["full_text"] == ""
    assert result["lines"] == []
    assert result["confidence"] is None
    assert "Application Control blocked PaddleOCR" in result["error"]


def test_demo_fallback_returns_fields_only_for_bundled_sample(monkeypatch):
    monkeypatch.setattr(ocr, "_get_paddle_engine", lambda: None)
    monkeypatch.setattr(ocr, "_paddle_error", "Application Control blocked PaddleOCR")
    monkeypatch.setattr(ocr.shutil, "which", lambda _: None)
    with Image.open(ocr.DEMO_CERTIFICATE_PATH) as sample:
        result = ocr.extract_text(sample.copy())

    assert result["status"] == "DEMO"
    assert result["engine"] == "Demo OCR Fallback"
    assert "Certificate ID: CERT001" in result["lines"]
    assert "Name: ARUN KUMAR" in result["lines"]
    assert "Register No: 21CS001" in result["lines"]
    assert "CGPA: 9.0" in result["lines"]
    assert result["confidence"] is None
    assert "approved OCR engine is unavailable" in result["error"]


def test_demo_fallback_does_not_fabricate_text_for_unknown_image(monkeypatch):
    monkeypatch.setattr(ocr, "_get_paddle_engine", lambda: None)
    monkeypatch.setattr(ocr, "_paddle_error", "Application Control blocked PaddleOCR")
    monkeypatch.setattr(ocr.shutil, "which", lambda _: None)
    result = ocr.extract_text(Image.new("RGB", (1600, 1000), "white"))

    assert result["status"] == "UNAVAILABLE"
    assert result["engine"] is None
    assert result["full_text"] == ""
    assert result["lines"] == []


def test_invalid_image_returns_clear_error():
    result = ocr.extract_text(b"not an image")
    assert result["status"] == "ERROR"
    assert result["text"] == ""
    assert result["full_text"] == ""
    assert result["lines"] == []
    assert result["confidence"] is None
    assert "Could not read the image" in result["error"]
