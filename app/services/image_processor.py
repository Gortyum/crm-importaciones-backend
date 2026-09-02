import io
import os
import uuid

from PIL import Image, ImageEnhance
from rembg import remove

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
ORIG_DIR = os.path.join(UPLOAD_DIR, "originals")
PROCESSED_DIR = UPLOAD_DIR

MAX_DIMENSION = 1200
QUALITY = 78


def _ensure_dirs():
    os.makedirs(ORIG_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)


def _strip_exif(img: Image.Image) -> Image.Image:
    data = list(img.getdata())
    clean = Image.new(img.mode, img.size)
    clean.putdata(data)
    return clean


def _remove_background(img: Image.Image) -> Image.Image:
    result = remove(img)
    white_bg = Image.new("RGBA", result.size, (255, 255, 255, 255))
    white_bg.paste(result, mask=result.split()[3])
    return white_bg.convert("RGB")


def _auto_crop(img: Image.Image) -> Image.Image:
    bg = Image.new("RGB", img.size, (255, 255, 255))
    diff = Image.eval(img, lambda p: 255 - p)
    bbox = diff.getbbox()
    if bbox:
        padding = 20
        bbox = (
            max(0, bbox[0] - padding),
            max(0, bbox[1] - padding),
            min(img.width, bbox[2] + padding),
            min(img.height, bbox[3] + padding),
        )
        return img.crop(bbox)
    return img


def _adjust(img: Image.Image) -> Image.Image:
    img = ImageEnhance.Brightness(img).enhance(1.05)
    img = ImageEnhance.Contrast(img).enhance(1.05)
    img = ImageEnhance.Color(img).enhance(1.03)
    img = ImageEnhance.Sharpness(img).enhance(1.15)
    return img


def _resize(img: Image.Image) -> Image.Image:
    w, h = img.size
    if max(w, h) <= MAX_DIMENSION:
        return img
    ratio = MAX_DIMENSION / max(w, h)
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    return img.resize((new_w, new_h), Image.LANCZOS)


def process_image(file_contents: bytes, original_filename: str) -> dict:
    _ensure_dirs()

    orig_id = uuid.uuid4().hex
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "jpg"
    orig_filename = f"{orig_id}.{ext}"
    orig_path = os.path.join(ORIG_DIR, orig_filename)
    with open(orig_path, "wb") as f:
        f.write(file_contents)

    img = Image.open(io.BytesIO(file_contents))
    img = _strip_exif(img)
    img = _remove_background(img)
    img = _auto_crop(img)
    img = _adjust(img)
    img = _resize(img)

    proc_filename = f"{uuid.uuid4().hex}.webp"
    proc_path = os.path.join(PROCESSED_DIR, proc_filename)
    img.save(proc_path, format="WEBP", quality=QUALITY, method=4)

    return {
        "url": f"/uploads/{proc_filename}",
        "filename": proc_filename,
        "original_filename": orig_filename,
    }
