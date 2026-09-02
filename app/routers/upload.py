from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.image_processor import process_image

router = APIRouter(prefix="/api/upload", tags=["upload"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/")
async def upload_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Tipo de archivo no permitido: {file.content_type}")

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(400, "El archivo supera los 10MB")

    try:
        result = process_image(contents, file.filename or "image.jpg")
    except Exception as e:
        raise HTTPException(500, f"Error procesando imagen: {str(e)}")

    return result
