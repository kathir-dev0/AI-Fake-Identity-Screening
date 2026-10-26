import csv
import io
import os
import shutil
import subprocess
from importlib.metadata import PackageNotFoundError, version
import inspect

import numpy as np
from PIL import Image, ImageOps

from config import BASE_DIR


os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("FLAGS_allocator_strategy", "auto_growth")

_paddle_engine = None
_paddle_error = None
DEMO_CERTIFICATE_PATH = BASE_DIR / "sample_data" / "genuine" / "veridoc_demo_certificate.png"
DEMO_OCR_NOTE = (
	"Demo OCR fallback is used because an approved OCR engine is unavailable "
	"in the current environment."
)
DEMO_CERTIFICATE_LINES = [
	"FICTIONAL SYNTHETIC DEMO CERTIFICATE",
	"Certificate ID: CERT001",
	"Name: ARUN KUMAR",
	"Register No: 21CS001",
	"CGPA: 9.0",
]


class OCREngineUnavailable(RuntimeError):
	pass


def _image_array(image):
	if isinstance(image, Image.Image):
		pil_image = image
	elif isinstance(image, (bytes, bytearray)):
		pil_image = Image.open(io.BytesIO(image))
	else:
		pil_image = Image.fromarray(np.asarray(image))
	return np.asarray(ImageOps.exif_transpose(pil_image).convert("RGB"))


def _is_exact_demo_certificate(image_array):
	try:
		with Image.open(DEMO_CERTIFICATE_PATH) as demo_image:
			demo_array = np.asarray(
				ImageOps.exif_transpose(demo_image).convert("RGB")
			)
		return image_array.shape == demo_array.shape and np.array_equal(image_array, demo_array)
	except (OSError, ValueError):
		return False


def _get_paddle_engine():
	global _paddle_engine, _paddle_error
	if _paddle_engine is not None:
		return _paddle_engine
	if _paddle_error is not None:
		return None

	try:
		from paddleocr import PaddleOCR

		try:
			installed_version = version("paddleocr")
		except PackageNotFoundError:
			installed_version = "unknown"
		if installed_version.split(".", maxsplit=1)[0] == "3":
			options = {"lang": "en", "use_textline_orientation": True}
		else:
			parameters = inspect.signature(PaddleOCR).parameters
			options = {"lang": "en"}
			if "use_angle_cls" in parameters:
				options["use_angle_cls"] = True
			if "show_log" in parameters:
				options["show_log"] = False
		_paddle_engine = PaddleOCR(**options)
		return _paddle_engine
	except Exception as error:
		_paddle_error = f"{type(error).__name__}: {error}"
		return None


def _parse_paddle_result(result):
	lines = []
	boxes = []
	confidences = []

	def add(text, box=None, confidence=None):
		if text:
			lines.append(str(text))
			boxes.append(box)
			try:
				confidences.append(float(confidence))
			except (TypeError, ValueError):
				confidences.append(None)

	def is_legacy_line(item):
		return (
			isinstance(item, (list, tuple))
			and len(item) == 2
			and isinstance(item[1], (list, tuple))
			and len(item[1]) >= 2
			and isinstance(item[1][0], str)
		)

	if isinstance(result, dict):
		texts = result.get("rec_texts", [])
		scores = result.get("rec_scores", [])
		found_boxes = result.get("dt_polys", result.get("rec_boxes", []))
		for index, text in enumerate(texts):
			box = np.asarray(found_boxes[index]).tolist() if index < len(found_boxes) else None
			add(text, box, scores[index] if index < len(scores) else None)
		return lines, boxes, confidences

	if hasattr(result, "json"):
		payload = result.json
		if callable(payload):
			payload = payload()
		if isinstance(payload, dict):
			return _parse_paddle_result(payload.get("res", payload))

	if isinstance(result, (list, tuple)):
		for item in result:
			if hasattr(item, "json") or isinstance(item, dict):
				child_lines, child_boxes, child_scores = _parse_paddle_result(item)
				lines.extend(child_lines)
				boxes.extend(child_boxes)
				confidences.extend(child_scores)
			elif is_legacy_line(item):
				recognition = item[1]
				box = np.asarray(item[0]).tolist() if item[0] is not None else None
				add(recognition[0], box, recognition[1])
			elif isinstance(item, (list, tuple)):
				child_lines, child_boxes, child_scores = _parse_paddle_result(item)
				lines.extend(child_lines)
				boxes.extend(child_boxes)
				confidences.extend(child_scores)
		return lines, boxes, confidences

	return lines, boxes, confidences


def _make_result(lines=None, boxes=None, confidences=None, engine=None, error=None, status=None):
	lines = [str(line) for line in (lines or []) if str(line).strip()]
	confidences = confidences or []
	valid_confidences = [score for score in confidences if isinstance(score, (int, float))]
	confidence = (
		round(sum(valid_confidences) / len(valid_confidences), 4) if valid_confidences else None
	)
	full_text = "\n".join(lines)
	return {
		"full_text": full_text,
		"lines": lines,
		"confidence": confidence,
		"engine": engine,
		"error": error,
		"status": status or ("OK" if lines else "NO_TEXT"),
		"text": full_text,
		"boxes": boxes or [],
		"confidences": confidences,
	}


def _parse_tesseract_tsv(tsv_text):
	line_words = {}
	boxes = []
	confidences = []
	for row in csv.DictReader(io.StringIO(tsv_text), delimiter="\t"):
		word = (row.get("text") or "").strip()
		if not word:
			continue
		try:
			score = float(row.get("conf", "-1")) / 100
			box = [int(row[key]) for key in ("left", "top", "width", "height")]
		except (TypeError, ValueError, KeyError):
			continue
		if score < 0:
			continue
		line_key = tuple(row.get(key, "") for key in ("page_num", "block_num", "par_num", "line_num"))
		line_words.setdefault(line_key, []).append(word)
		boxes.append(box)
		confidences.append(score)
	lines = [" ".join(words) for words in line_words.values()]
	return lines, boxes, confidences


def _run_tesseract(image_array):
	"""Use an already-installed pytesseract binding or Tesseract executable."""
	python_error = None
	try:
		import pytesseract
		from pytesseract import Output

		data = pytesseract.image_to_data(
			Image.fromarray(image_array), output_type=Output.DICT
		)
		line_words = {}
		boxes = []
		confidences = []
		for index, raw_word in enumerate(data.get("text", [])):
			word = str(raw_word).strip()
			if not word:
				continue
			try:
				score = float(data["conf"][index]) / 100
				box = [int(data[key][index]) for key in ("left", "top", "width", "height")]
			except (KeyError, TypeError, ValueError):
				continue
			if score < 0:
				continue
			line_key = tuple(
				str(data.get(key, [""] * (index + 1))[index])
				for key in ("page_num", "block_num", "par_num", "line_num")
			)
			line_words.setdefault(line_key, []).append(word)
			boxes.append(box)
			confidences.append(score)
		lines = [" ".join(words) for words in line_words.values()]
		return lines, boxes, confidences
	except ImportError:
		pass
	except Exception as error:
		python_error = f"pytesseract failed: {type(error).__name__}: {error}"

	executable = shutil.which("tesseract")
	if executable is None:
		message = "Tesseract executable is not installed or is not on PATH."
		if python_error:
			message = f"{python_error}; {message}"
		raise OCREngineUnavailable(message)

	buffer = io.BytesIO()
	Image.fromarray(image_array).save(buffer, format="PNG")
	completed = subprocess.run(
		[executable, "stdin", "stdout", "--psm", "6", "tsv"],
		input=buffer.getvalue(),
		capture_output=True,
		check=False,
	)
	if completed.returncode != 0:
		stderr = completed.stderr.decode("utf-8", errors="replace").strip()
		raise RuntimeError(f"Tesseract exited with code {completed.returncode}: {stderr}")
	tsv_text = completed.stdout.decode("utf-8", errors="replace")
	return _parse_tesseract_tsv(tsv_text)


def extract_text(image):
	"""Run installed OCR engines, with a fingerprinted fictional demo fallback."""
	try:
		image_array = _image_array(image)
	except Exception as error:
		return _make_result(error=f"Could not read the image for OCR: {error}", status="ERROR")

	engine = _get_paddle_engine()
	paddle_error = _paddle_error
	paddle_failed = engine is None
	if engine is not None:
		try:
			if hasattr(engine, "predict"):
				try:
					paddle_result = engine.predict(image_array)
				except TypeError:
					paddle_result = engine.predict(input=image_array)
			else:
				try:
					paddle_result = engine.ocr(image_array, cls=True)
				except TypeError:
					paddle_result = engine.ocr(image_array)
			lines, boxes, confidences = _parse_paddle_result(paddle_result)
			if lines:
				return _make_result(lines, boxes, confidences, "PaddleOCR", status="OK")
			paddle_error = "PaddleOCR initialized but detected no text in this image."
		except Exception as error:
			paddle_error = f"PaddleOCR execution failed: {type(error).__name__}: {error}"
			paddle_failed = True

	try:
		lines, boxes, confidences = _run_tesseract(image_array)
		if lines:
			return _make_result(lines, boxes, confidences, "Tesseract", status="OK")
		return _make_result(
			engine="Tesseract",
			error="Tesseract ran but detected no text in this image.",
			status="NO_TEXT",
		)
	except OCREngineUnavailable as error:
		if paddle_failed and _is_exact_demo_certificate(image_array):
			return _make_result(
				DEMO_CERTIFICATE_LINES,
				engine="Demo OCR Fallback",
				error=DEMO_OCR_NOTE,
				status="DEMO",
			)
		fallback_error = f"Tesseract fallback unavailable: {type(error).__name__}: {error}"
		message = f"OCR unavailable. {paddle_error or 'PaddleOCR is not installed.'} {fallback_error}"
		return _make_result(error=message, status="UNAVAILABLE")
	except Exception as error:
		fallback_error = f"Tesseract fallback unavailable: {type(error).__name__}: {error}"
		message = f"OCR unavailable. {paddle_error or 'PaddleOCR is not installed.'} {fallback_error}"
		return _make_result(error=message, status="UNAVAILABLE")