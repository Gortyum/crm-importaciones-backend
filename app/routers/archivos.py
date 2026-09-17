import hashlib
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.archivo import Archivo
from app.models.usuario import Usuario
from app.routers.auth import obtener_usuario_actual
from app.schemas.archivo import ArchivoOut, ArchivoUploadResult
from app.services.storage import Almacen, AlmacenNulo, obtener_storage
from app.services.validacion_archivos import (
    CARPETAS,
    carpeta_para,
    limite_para,
    nombre_seguro,
    validar_extension,
)

router = APIRouter(prefix="/api/archivos", tags=["archivos"])


def _archivo_a_out(archivo: Archivo) -> ArchivoOut:
    url = obtener_storage().url(archivo.object_key, archivo.es_publico)
    return ArchivoOut(
        id=archivo.id,
        nombre_original=archivo.nombre_original,
        object_key=archivo.object_key,
        carpeta=archivo.carpeta,
        entidad_tipo=archivo.entidad_tipo,
        entidad_id=archivo.entidad_id,
        mime_type=archivo.mime_type,
        tamano=archivo.tamano,
        es_publico=archivo.es_publico,
        created_by=archivo.created_by,
        created_at=archivo.created_at,
        url=url,
    )


def _storage_o_503() -> Almacen:
    storage = obtener_storage()
    if isinstance(storage, AlmacenNulo):
        raise HTTPException(
            503,
            "Almacenamiento en la nube no configurado. Define R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, "
            "R2_SECRET_ACCESS_KEY y R2_BUCKET_NAME en el entorno.",
        )
    return storage


@router.post("/upload", response_model=ArchivoUploadResult, status_code=201)
async def subir_archivo(
    file: UploadFile = File(...),
    entidad_tipo: str = Form(...),
    entidad_id: int | None = Form(default=None),
    es_publico: bool = Form(default=False),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    """Sube un archivo a R2 y registra sus metadatos en PostgreSQL.

    Solo las imágenes de productos son públicas; cualquier otro archivo se
    almacena privado y se accede por URL firmada.
    """
    if entidad_tipo not in CARPETAS:
        raise HTTPException(400, f"entidad_tipo inválido: {entidad_tipo}. Usa: {', '.join(CARPETAS)}")
    if es_publico and entidad_tipo != "producto":
        raise HTTPException(400, "Solo las imágenes de productos pueden ser públicas")

    nombre_original = nombre_seguro(file.filename or "archivo")

    ext = nombre_original.rsplit(".", 1)[-1].lower() if "." in nombre_original else ""
    if not ext:
        raise HTTPException(400, "El archivo debe tener extensión")
    mime = (file.content_type or "").lower()
    validar_extension(entidad_tipo, ext, mime)

    contenido = await file.read()
    limite = limite_para(entidad_tipo)
    if len(contenido) == 0:
        raise HTTPException(400, "El archivo está vacío")
    if len(contenido) > limite:
        limite_mb = limite // (1024 * 1024)
        raise HTTPException(400, f"El archivo supera el máximo de {limite_mb}MB")

    carpeta = carpeta_para(entidad_tipo)
    object_key = f"{carpeta}/{uuid.uuid4().hex}.{ext}"

    # Dedup global por contenido: si el hash ya existe, se reutiliza el objeto
    # físico en R2 (una sola copia) y solo se crea una referencia nueva.
    file_hash = hashlib.sha256(contenido).hexdigest()
    existente = db.query(Archivo).filter(Archivo.hash_sha256 == file_hash).first()
    duplicado = existente is not None
    if duplicado:
        object_key = existente.object_key

    archivo = Archivo(
        nombre_original=nombre_original,
        object_key=object_key,
        hash_sha256=file_hash,
        carpeta=carpeta,
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        mime_type=file.content_type,
        tamano=len(contenido),
        es_publico=es_publico,
        created_by=usuario.username,
    )
    db.add(archivo)

    storage = _storage_o_503()
    try:
        if not duplicado:
            storage.subir(object_key, contenido, mime)
    except Exception as exc:
        db.rollback()
        raise HTTPException(502, f"Error subiendo a R2: {type(exc).__name__}")

    db.commit()
    db.refresh(archivo)

    return ArchivoUploadResult(
        id=archivo.id,
        nombre_original=archivo.nombre_original,
        object_key=archivo.object_key,
        carpeta=archivo.carpeta,
        entidad_tipo=archivo.entidad_tipo,
        entidad_id=archivo.entidad_id,
        mime_type=archivo.mime_type,
        tamano=archivo.tamano,
        es_publico=archivo.es_publico,
        url=storage.url(object_key, es_publico),
        duplicado=duplicado,
    )


@router.get("/", response_model=list[ArchivoOut])
def listar_archivos(
    entidad_tipo: str,
    entidad_id: int | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Archivo).filter(Archivo.entidad_tipo == entidad_tipo)
    if entidad_id is not None:
        q = q.filter(Archivo.entidad_id == entidad_id)
    return [_archivo_a_out(a) for a in q.order_by(Archivo.created_at.desc()).all()]


@router.get("/{archivo_id}", response_model=ArchivoOut)
def obtener_archivo(archivo_id: int, db: Session = Depends(get_db)):
    archivo = db.query(Archivo).get(archivo_id)
    if not archivo:
        raise HTTPException(404, "Archivo no encontrado")
    return _archivo_a_out(archivo)


@router.get("/{archivo_id}/descargar")
def descargar_archivo(
    archivo_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    """Redirige a una URL firmada temporal. Requiere autenticación (JWT).

    La URL firmada vence en 15 minutos; el navegador o cliente descarga
    directamente desde R2 sin pasar el archivo por Railway.
    """
    archivo = db.query(Archivo).get(archivo_id)
    if not archivo:
        raise HTTPException(404, "Archivo no encontrado")
    return RedirectResponse(_storage_o_503().url_firmada(archivo.object_key, 900))


@router.get("/{archivo_id}/contenido")
def contenido_archivo(
    archivo_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    """Devuelve el contenido del archivo por el propio backend (same-origin).

    Permite renderizar imágenes en canvas/PDF sin necesidad de CORS en R2.
    """
    archivo = db.query(Archivo).get(archivo_id)
    if not archivo:
        raise HTTPException(404, "Archivo no encontrado")
    try:
        contenido = _storage_o_503().contenido(archivo.object_key)
    except Exception as exc:
        raise HTTPException(502, f"Error leyendo archivo: {type(exc).__name__}")
    return Response(contenido, media_type=archivo.mime_type or "application/octet-stream")


@router.delete("/{archivo_id}", status_code=204)
def eliminar_archivo(
    archivo_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    archivo = db.query(Archivo).get(archivo_id)
    if not archivo:
        raise HTTPException(404, "Archivo no encontrado")

    otras_referencias = (
        db.query(Archivo).filter(Archivo.object_key == archivo.object_key, Archivo.id != archivo.id).count()
    )
    if otras_referencias == 0:
        # Última referencia al objeto: se elimina físicamente de R2 (si hay R2).
        storage = obtener_storage()
        if not isinstance(storage, AlmacenNulo):
            try:
                storage.eliminar(archivo.object_key)
            except Exception:
                db.delete(archivo)
                db.commit()
                raise HTTPException(502, "No se pudo eliminar el archivo en R2")

    db.delete(archivo)
    db.commit()