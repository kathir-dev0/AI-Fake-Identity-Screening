"""
Synthetic Document Generator and OCR Test Script
Creates a test identity card image and runs PaddleOCR on it to verify recognition.
"""
from PIL import Image, ImageDraw, ImageFont
import os
import sys

# Ensure services can be imported
sys.path.insert(0, os.path.abspath("."))
from services.ocr_service import extract_document_text

def create_synthetic_doc(output_path="data/test_synthetic_document.png"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Create white document canvas with high resolution
    width, height = 800, 500
    img = Image.new("RGB", (width, height), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)
    
    # Outer border / card outline
    draw.rounded_rectangle([20, 20, width - 20, height - 20], radius=15, outline=(180, 190, 205), width=3)
    
    # Header banner
    draw.rectangle([25, 25, width - 25, 80], fill=(225, 235, 245))
    
    # Try default or standard font
    try:
        font_header = ImageFont.truetype("arial.ttf", 22)
        font_body = ImageFont.truetype("arial.ttf", 24)
        font_disclaimer = ImageFont.truetype("arial.ttf", 16)
    except IOError:
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_disclaimer = ImageFont.load_default()
        
    # Draw Header Text
    header_text = "TEST DOCUMENT — NOT VALID FOR IDENTIFICATION"
    draw.text((40, 42), header_text, fill=(180, 30, 30), font=font_header)
    
    # Draw fields
    fields = [
        "Name: ARUN KUMAR",
        "Document Number: TEST12345",
        "Nationality: IND",
        "Date of Birth: 14/07/2002",
        "Gender: M",
        "Date of Expiry: 14/07/2032"
    ]
    
    y = 120
    for field in fields:
        draw.text((50, y), field, fill=(20, 25, 35), font=font_body)
        y += 48
        
    img.save(output_path)
    print(f"Synthetic document saved to {output_path}")
    return output_path

if __name__ == "__main__":
    img_path = create_synthetic_doc()
    img = Image.open(img_path)
    res = extract_document_text(img)
    print("\n--- OCR RESULTS ---")
    print("Success:", res["success"])
    print("Line Count:", res["line_count"])
    print("Average Confidence:", res["avg_confidence"])
    print("\nFull Text:\n", res["full_text"])
