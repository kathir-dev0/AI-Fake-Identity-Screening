import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from config import BASE_DIR


_face_analyzer = None
_face_error = None
FACE_MATCH_THRESHOLD = 0.40


def _to_rgb_array(image):
	if isinstance(image, Image.Image):
		source = image
	elif isinstance(image, (bytes, bytearray)):
		source = Image.open(io.BytesIO(image))
	else:
		source = Image.fromarray(np.asarray(image))
	return np.asarray(ImageOps.exif_transpose(source).convert("RGB"))


def _get_analyzer():
	global _face_analyzer, _face_error
	if _face_analyzer is not None:
		return _face_analyzer
	if _face_error is not None:
		return None
	try:
		from insightface.app import FaceAnalysis

		analyzer = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
		analyzer.prepare(ctx_id=-1, det_size=(640, 640))
		_face_analyzer = analyzer
		return _face_analyzer
	except Exception as error:
		_face_error = str(error)
		return None


def _largest_embedding(analyzer, image):
	rgb = _to_rgb_array(image)
	faces = analyzer.get(rgb[:, :, ::-1])
	if not faces:
		return None
	face = max(
		faces,
		key=lambda item: float((item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])),
	)
	embedding = getattr(face, "normed_embedding", None)
	if embedding is None:
		embedding = getattr(face, "embedding", None)
	if embedding is None:
		return None
	embedding = np.asarray(embedding, dtype=np.float32)
	norm = np.linalg.norm(embedding)
	return embedding / norm if norm else None


def verify_face(document_image, reference_face=None):
	"""Compare the largest detected face using InsightFace cosine similarity."""
	if not reference_face:
		return {
			"status": "NOT_AVAILABLE",
			"face_detected": None,
			"similarity": None,
			"match": None,
			"reason": "No trusted reference face is attached to this demo record.",
		}

	analyzer = _get_analyzer()
	if analyzer is None:
		return {
			"status": "UNAVAILABLE",
			"face_detected": None,
			"similarity": None,
			"match": None,
			"reason": f"InsightFace is unavailable: {_face_error}",
		}

	reference_path = Path(reference_face)
	if not reference_path.is_absolute():
		reference_path = BASE_DIR / reference_path
	if not reference_path.is_file():
		return {
			"status": "NOT_AVAILABLE",
			"face_detected": None,
			"similarity": None,
			"match": None,
			"reason": "The trusted reference face image file is unavailable.",
		}

	try:
		with Image.open(reference_path) as reference_image:
			document_embedding = _largest_embedding(analyzer, document_image)
			reference_embedding = _largest_embedding(analyzer, reference_image.copy())
		if document_embedding is None or reference_embedding is None:
			return {
				"status": "NO_FACE",
				"face_detected": document_embedding is not None,
				"similarity": None,
				"match": None,
				"reason": "A usable face was not detected in both images.",
			}
		similarity = float(np.dot(document_embedding, reference_embedding))
		matched = similarity >= FACE_MATCH_THRESHOLD
		return {
			"status": "COMPARED",
			"face_detected": True,
			"similarity": round(similarity, 4),
			"match": matched,
			"reason": "Face similarity is above the demo threshold." if matched else "Face similarity is below the demo threshold.",
		}
	except Exception as error:
		return {
			"status": "ERROR",
			"face_detected": None,
			"similarity": None,
			"match": None,
			"reason": f"Face comparison could not be completed: {error}",
		}
