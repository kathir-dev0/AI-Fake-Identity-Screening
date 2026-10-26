import io

import numpy as np
from PIL import Image, ImageChops, ImageFilter, ImageOps


def _load_image(image):
	if isinstance(image, Image.Image):
		source = image.copy()
	elif isinstance(image, (bytes, bytearray)):
		source = Image.open(io.BytesIO(image))
	else:
		source = Image.fromarray(np.asarray(image))
	return ImageOps.exif_transpose(source).convert("RGB")


def _grid_means(array, rows=4, columns=4):
	height, width = array.shape[:2]
	values = []
	bounds = []
	for row in range(rows):
		top = row * height // rows
		bottom = (row + 1) * height // rows
		for column in range(columns):
			left = column * width // columns
			right = (column + 1) * width // columns
			values.append(float(np.mean(array[top:bottom, left:right])))
			bounds.append((left, top, right, bottom))
	return np.asarray(values), bounds


def analyze_tampering(image):
	"""Estimate possible manipulation indicators; ELA is not proof of forgery."""
	try:
		original = _load_image(image)
		if original.width < 48 or original.height < 48:
			raise ValueError("Image is too small for meaningful image-forensics checks.")

		compressed_buffer = io.BytesIO()
		original.save(compressed_buffer, format="JPEG", quality=90)
		compressed_buffer.seek(0)
		recompressed = Image.open(compressed_buffer).convert("RGB")
		ela = np.asarray(ImageChops.difference(original, recompressed), dtype=np.float32).mean(axis=2)
		ela_mean = float(np.mean(ela))

		grayscale = original.convert("L")
		median = grayscale.filter(ImageFilter.MedianFilter(size=3))
		residual = np.abs(
			np.asarray(grayscale, dtype=np.float32) - np.asarray(median, dtype=np.float32)
		)
		residual_means, _ = _grid_means(residual)
		residual_average = float(np.mean(residual_means))
		residual_spread = float(np.std(residual_means) / (residual_average + 1.0))

		ela_means, bounds = _grid_means(ela)
		median_ela = float(np.median(ela_means))
		deviation = float(np.median(np.abs(ela_means - median_ela)))
		threshold = max(18.0, median_ela + 3.0 * max(deviation, 1.0))
		suspicious_regions = []
		for value, (left, top, right, bottom) in zip(ela_means, bounds):
			if value > threshold:
				suspicious_regions.append(
					{"left": left, "top": top, "right": right, "bottom": bottom, "ela_mean": round(value, 2)}
				)

		ela_signal = min(1.0, ela_mean / 70.0)
		noise_signal = min(1.0, residual_spread / 3.0)
		region_signal = min(1.0, len(suspicious_regions) / 5.0)
		score = min(1.0, max(0.0, 0.5 * ela_signal + 0.35 * noise_signal + 0.15 * region_signal))

		if score < 0.30:
			level = "LOW INDICATION"
			message = "No strong image manipulation indicators were measured; this does not establish authenticity."
		elif score < 0.65:
			level = "MEDIUM INDICATION"
			message = "Some local image inconsistencies were measured; manual review is recommended."
		else:
			level = "HIGH INDICATION"
			message = "Strong image inconsistencies were measured; they require secondary review and are not proof of forgery."

		metadata_keys = sorted(str(key) for key in original.info.keys())
		return {
			"status": "ANALYZED",
			"tampering_score": round(score, 3),
			"level": level,
			"suspicious_regions": suspicious_regions[:8],
			"metadata_keys": metadata_keys,
			"metrics": {
				"ela_mean": round(ela_mean, 3),
				"noise_inconsistency": round(residual_spread, 3),
				"high_ela_regions": len(suspicious_regions),
			},
			"message": message,
		}
	except Exception as error:
		return {
			"status": "NOT_AVAILABLE",
			"tampering_score": 0.0,
			"level": "NOT_AVAILABLE",
			"suspicious_regions": [],
			"metadata_keys": [],
			"metrics": {},
			"message": f"Image-forensics analysis unavailable: {error}",
		}
