from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.image_processor import process_image
from app.services.validacion_archivos import MAX_IMG, validar_extension

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/")
async def upload_image(file: UploadFile = File(...)):
    ext = (file.filename or "image.jpg").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if not ext:
        raise HTTPException(400, "El archivo debe tener extensión")
    validar_extension("producto", ext, (file.content_type or "").lower())

    contents = await file.read()
    if len(contents) > MAX_IMG:
        raise HTTPException(400, "El archivo supera los 10MB")

    try:
        result = process_image(contents, file.filename or "image.jpg")
    except Exception as e:
        raise HTTPException(500, f"Error procesando imagen: {str(e)}")

    return result