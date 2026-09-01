"""
Image processing and WebP conversion service.
Handles validation, EXIF stripping, downscaling, and compression to WebP.
"""
import io
import os
import secrets
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageOps

# Maximum allowed upload size (5 MB)
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
MAX_DIMENSION = 1600
WEBP_QUALITY = 80

# Magic bytes detection
MAGIC_BYTES_MAP = {
    b"\xff\xd8\xff": "jpeg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"RIFF": "webp",  # RIFF....WEBP
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"ftypheic": "heic",
    b"ftypmif1": "heic",
    b"ftypheix": "heic",
}

# Upload directory on local disk
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "reviews"


def ensure_upload_dir() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def validate_image_bytes(data: bytes) -> Tuple[bool, str]:
    """
    Validate size and magic bytes of the image buffer.
    """
    if not data:
        return False, "Empty file provided."

    if len(data) > MAX_IMAGE_SIZE_BYTES:
        return False, f"Image size exceeds maximum limit of {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB."

    # Check magic bytes
    header_12 = data[:12]
    matched = False

    if data.startswith(b"\xff\xd8\xff"):
        matched = True
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        matched = True
    elif data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        matched = True
    elif data.startswith(b"RIFF") and b"WEBP" in header_12:
        matched = True
    elif b"ftyp" in header_12:
        matched = True

    if not matched:
        return False, "Unsupported or invalid image file format."

    return True, "Valid"


def process_and_save_webp(image_bytes: bytes) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates, strips EXIF, downscales if > 1600px, and converts image to WebP.
    Returns: (success: bool, photo_url: Optional[str], error_message: Optional[str])
    """
    is_valid, err = validate_image_bytes(image_bytes)
    if not is_valid:
        return False, None, err

    try:
        # Load image via Pillow
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Handle EXIF orientation (rotates properly if taken with phone camera)
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass  # Ignore if transposition is unsupported

            # Convert color modes to RGB or RGBA for WebP compatibility
            if img.mode in ("CMYK", "P", "LA", "I", "F"):
                img = img.convert("RGBA" if "A" in img.mode else "RGB")

            # Downscale if long edge exceeds MAX_DIMENSION
            width, height = img.size
            if max(width, height) > MAX_DIMENSION:
                scale = MAX_DIMENSION / max(width, height)
                new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Generate unique unguessable filename
            ensure_upload_dir()
            unique_name = f"rev_{secrets.token_hex(16)}.webp"
            save_path = UPLOAD_DIR / unique_name

            # Save as WebP (stripping EXIF by not passing exif param)
            img.save(save_path, format="WEBP", quality=WEBP_QUALITY, method=6)

            photo_url = f"/uploads/reviews/{unique_name}"
            return True, photo_url, None

    except Exception as e:
        return False, None, f"Image processing failed: {str(e)}"
