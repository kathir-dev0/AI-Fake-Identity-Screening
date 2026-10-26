"""
Face Detection and Portrait Extraction Service
Smart India Hackathon (SIH) Problem Statement: SIH26188

Provides modular, OpenCV-based facial detection and portrait region extraction
for identity document images (e.g., Passports, Driving Licenses, National IDs).

Key Features:
- Preserves original document image untouched (all annotations on copies).
- Robust Haar Cascade detection (primary + high-recall fallback with IoU deduplication).
- Clean bounding box annotations and cropped portrait generation.
- Graceful error handling for missing, corrupted, or multi-channel images.
- SIH Compliance: Does not authenticate identity or identify individuals by name.
"""

from typing import List, Dict, Any, Tuple, Optional
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Check OpenCV availability
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False


def _calculate_iou(box_a: Tuple[int, int, int, int], box_b: Tuple[int, int, int, int]) -> float:
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.
    Boxes are in format: (x, y, w, h)
    """
    xa1, ya1, wa, ha = box_a
    xa2, ya2 = xa1 + wa, ya1 + ha

    xb1, yb1, wb, hb = box_b
    xb2, yb2 = xb1 + wb, yb1 + hb

    # Determine coordinates of intersection rectangle
    inter_x1 = max(xa1, xb1)
    inter_y1 = max(ya1, yb1)
    inter_x2 = min(xa2, xb2)
    inter_y2 = min(ya2, yb2)

    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    # Compute individual areas
    area_a = wa * ha
    area_b = wb * hb

    union_area = area_a + area_b - inter_area
    if union_area <= 0:
        return 0.0

    return inter_area / union_area


def _deduplicate_boxes(boxes: List[Tuple[int, int, int, int]], iou_threshold: float = 0.35) -> List[Tuple[int, int, int, int]]:
    """
    Remove overlapping detections based on IoU threshold, prioritizing larger boxes.
    """
    if not boxes:
        return []

    # Sort boxes by area descending (w * h)
    sorted_boxes = sorted(boxes, key=lambda b: b[2] * b[3], reverse=True)
    kept_boxes: List[Tuple[int, int, int, int]] = []

    for box in sorted_boxes:
        overlap = False
        for kept in kept_boxes:
            if _calculate_iou(box, kept) > iou_threshold:
                overlap = True
                break
        if not overlap:
            kept_boxes.append(box)

    # Sort by spatial position (left-to-right, top-to-bottom)
    return sorted(kept_boxes, key=lambda b: (b[1] // 50, b[0]))


def _load_cascades() -> List[Any]:
    """Load OpenCV pre-trained Haar Cascades."""
    if not OPENCV_AVAILABLE:
        return []

    cascades = []
    haar_dir = getattr(cv2, "data", None)
    if haar_dir and hasattr(haar_dir, "haarcascades"):
        base_path = haar_dir.haarcascades
        primary_path = os.path.join(base_path, "haarcascade_frontalface_default.xml")
        alt_path = os.path.join(base_path, "haarcascade_frontalface_alt2.xml")

        if os.path.exists(primary_path):
            clf = cv2.CascadeClassifier(primary_path)
            if not clf.empty():
                cascades.append(clf)

        if os.path.exists(alt_path):
            clf_alt = cv2.CascadeClassifier(alt_path)
            if not clf_alt.empty():
                cascades.append(clf_alt)

    return cascades


def detect_faces(
    image: Image.Image,
    scale_factor: float = 1.1,
    min_neighbors: int = 5,
    min_size: Tuple[int, int] = (40, 40),
    margin_ratio: float = 0.15
) -> Dict[str, Any]:
    """
    Detects faces in an uploaded document image and extracts cropped portraits.

    Parameters:
        image: PIL Image object of the identity document.
        scale_factor: Parameter specifying how much the image size is reduced at each image scale.
        min_neighbors: Number of neighbors each candidate rectangle should retain.
        min_size: Minimum possible object size. Objects smaller than that are ignored.
        margin_ratio: Relative margin around detected face box for natural portrait cropping.

    Returns:
        dict containing:
            - success (bool): True if detection completed without fatal error.
            - face_count (int): Total number of distinct faces detected.
            - faces (list): List of dicts for each detected face, containing:
                - index (int): 1-based index
                - box (tuple): (x, y, w, h) in original image coordinates
                - crop_box (tuple): (x1, y1, x2, y2) bounds of the extracted portrait
                - cropped_image (PIL.Image): Cropped portrait image
                - width (int): Bounding box width
                - height (int): Bounding box height
            - annotated_image (PIL.Image): Copy of original image with bounding boxes drawn.
            - error (str or None): Error message if detection failed.
    """
    if not OPENCV_AVAILABLE:
        return {
            "success": False,
            "face_count": 0,
            "faces": [],
            "annotated_image": None,
            "error": "OpenCV library is not available in the current environment."
        }

    if image is None:
        return {
            "success": False,
            "face_count": 0,
            "faces": [],
            "annotated_image": None,
            "error": "No image provided for face detection."
        }

    try:
        # Convert PIL image to RGB if necessary (handles RGBA, P, L, CMYK)
        if image.mode != "RGB":
            pil_rgb = image.convert("RGB")
        else:
            pil_rgb = image

        img_w, img_h = pil_rgb.size
        np_img = np.array(pil_rgb)

        # Convert to Grayscale for Haar Cascade
        gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)

        # Apply histogram equalization to normalize varying document lighting/contrast
        gray_eq = cv2.equalizeHist(gray)

        cascades = _load_cascades()
        if not cascades:
            return {
                "success": False,
                "face_count": 0,
                "faces": [],
                "annotated_image": None,
                "error": "Failed to load OpenCV Haar Cascade classifiers."
            }

        raw_detected_boxes: List[Tuple[int, int, int, int]] = []

        # Run primary cascade
        primary_faces = cascades[0].detectMultiScale(
            gray,
            scaleFactor=scale_factor,
            minNeighbors=min_neighbors,
            minSize=min_size
        )
        for (x, y, w, h) in primary_faces:
            raw_detected_boxes.append((int(x), int(y), int(w), int(h)))

        # Also run on equalized image if no faces found
        if not raw_detected_boxes and len(cascades) > 0:
            eq_faces = cascades[0].detectMultiScale(
                gray_eq,
                scaleFactor=scale_factor,
                minNeighbors=min_neighbors,
                minSize=min_size
            )
            for (x, y, w, h) in eq_faces:
                raw_detected_boxes.append((int(x), int(y), int(w), int(h)))

        # If still no faces or fallback cascade available, try alt2 cascade
        if len(cascades) > 1 and len(raw_detected_boxes) == 0:
            alt_faces = cascades[1].detectMultiScale(
                gray,
                scaleFactor=scale_factor,
                minNeighbors=min_neighbors,
                minSize=min_size
            )
            for (x, y, w, h) in alt_faces:
                raw_detected_boxes.append((int(x), int(y), int(w), int(h)))

        # Deduplicate overlapping boxes
        distinct_boxes = _deduplicate_boxes(raw_detected_boxes)
        face_count = len(distinct_boxes)

        # Create a deep copy of the original image for annotation
        annotated_image = pil_rgb.copy()
        draw = ImageDraw.Draw(annotated_image)

        # Load font for labels if available
        try:
            label_font = ImageFont.truetype("arial.ttf", max(14, int(img_h * 0.025)))
        except (IOError, OSError):
            label_font = ImageFont.load_default()

        # Box styling colors
        box_color = (0, 220, 255)       # High-contrast cyan/teal
        tag_bg_color = (15, 23, 42)      # Deep slate pill background
        tag_text_color = (255, 255, 255) # White text

        face_records: List[Dict[str, Any]] = []

        for idx, (x, y, w, h) in enumerate(distinct_boxes, start=1):
            # Calculate padded cropping box with margin
            pad_w = int(w * margin_ratio)
            pad_h = int(h * margin_ratio)

            crop_x1 = max(0, x - pad_w)
            crop_y1 = max(0, y - pad_h)
            crop_x2 = min(img_w, x + w + pad_w)
            crop_y2 = min(img_h, y + h + pad_h)

            cropped_portrait = pil_rgb.crop((crop_x1, crop_y1, crop_x2, crop_y2))

            face_records.append({
                "index": idx,
                "box": (x, y, w, h),
                "crop_box": (crop_x1, crop_y1, crop_x2, crop_y2),
                "cropped_image": cropped_portrait,
                "width": w,
                "height": h
            })

            # Draw bounding box on annotated copy (thickness proportional to image size)
            line_width = max(3, int(min(img_w, img_h) * 0.005))
            draw.rectangle([x, y, x + w, y + h], outline=box_color, width=line_width)

            # Draw label pill above the box
            label_text = f"Face #{idx} ({w}x{h})"
            
            # Determine text size
            if hasattr(draw, "textbbox"):
                bbox = draw.textbbox((0, 0), label_text, font=label_font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
            else:
                text_w, text_h = 100, 18

            pill_pad = 4
            pill_y1 = max(0, y - text_h - pill_pad * 2 - 2)
            pill_y2 = pill_y1 + text_h + pill_pad * 2
            pill_x1 = x
            pill_x2 = min(img_w, x + text_w + pill_pad * 2)

            # Draw pill background and text
            draw.rectangle([pill_x1, pill_y1, pill_x2, pill_y2], fill=tag_bg_color, outline=box_color, width=1)
            draw.text((pill_x1 + pill_pad, pill_y1 + pill_pad), label_text, fill=tag_text_color, font=label_font)

        return {
            "success": True,
            "face_count": face_count,
            "faces": face_records,
            "annotated_image": annotated_image,
            "error": None
        }

    except Exception as err:
        return {
            "success": False,
            "face_count": 0,
            "faces": [],
            "annotated_image": None,
            "error": f"Face detection error: {str(err)}"
        }
