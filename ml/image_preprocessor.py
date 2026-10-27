"""
Image Preprocessing Pipeline for Medical Prescription OCR.
Handles orientation correction, contrast enhancement, shadow reduction,
and stroke preservation for handwritten prescriptions.
"""

import os
from typing import Tuple, Dict, Any, Optional
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
MAX_DIMENSION = 2048  # Downscale if exceeding to keep inference efficient
MIN_DIMENSION = 50    # Reject tiny unreadable images
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB max upload size

def validate_image_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """Validate image file exists, within allowed size, allowed extension, and is a valid image."""
    if not os.path.exists(file_path):
        return False, "File does not exist"
    
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE_BYTES:
        return False, f"File size ({round(file_size / (1024 * 1024), 2)}MB) exceeds maximum limit of 15MB"

    if file_size == 0:
        return False, "Uploaded image file is empty (0 bytes)"

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True, None
    except Exception as e:
        return False, f"Corrupted or unreadable image file: {str(e)}"

def preprocess_prescription_image(
    image_input: Any,
    enhance_contrast: bool = True,
    max_dimension: int = MAX_DIMENSION
) -> Tuple[Image.Image, Dict[str, Any]]:
    """
    Applies sensible image preprocessing tailored for handwritten medical prescriptions:
    1. EXIF orientation correction.
    2. RGB conversion.
    3. Dimension scaling (downscales oversized scans to optimize memory/speed while keeping strokes sharp).
    4. Adaptive contrast stretching (autocontrast with gentle cutoff).
    5. Gentle contrast enhancement to pop handwritten ink from paper texture.
    6. Subtle stroke sharpening without noisy binarization.
    """
    metadata: Dict[str, Any] = {}
    
    # 1. Open image
    if isinstance(image_input, str):
        img = Image.open(image_input)
    elif isinstance(image_input, Image.Image):
        img = image_input.copy()
    else:
        img = Image.open(image_input)
        
    metadata["original_size"] = img.size
    metadata["original_mode"] = img.mode

    # 2. Correct EXIF orientation
    try:
        img = ImageOps.exif_transpose(img)
        metadata["orientation_corrected"] = True
    except Exception:
        metadata["orientation_corrected"] = False

    # 3. Convert to RGB
    if img.mode != "RGB":
        img = img.convert("RGB")

    # 4. Dimension scaling (maintain aspect ratio)
    w, h = img.size
    max_side = max(w, h)
    if max_side > max_dimension:
        scale = max_dimension / float(max_side)
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        metadata["resized"] = True
        metadata["processed_size"] = (new_w, new_h)
    else:
        metadata["resized"] = False
        metadata["processed_size"] = (w, h)

    # 5. Contrast and lighting enhancement (preserving faint handwriting strokes)
    if enhance_contrast:
        # Autocontrast: normalize histogram with 0.5% cutoff for paper margins
        img = ImageOps.autocontrast(img, cutoff=0.5)
        
        # Gentle contrast boost (1.2x)
        contrast_enhancer = ImageEnhance.Contrast(img)
        img = contrast_enhancer.enhance(1.2)
        
        # Subtle sharpening to strengthen pen/pencil lines
        img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=110, threshold=2))
        metadata["contrast_enhanced"] = True
    else:
        metadata["contrast_enhanced"] = False

    return img, metadata
