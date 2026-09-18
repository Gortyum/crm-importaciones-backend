"""Resolución fresca de URLs de imagen de producto.

Las URLs firmadas de R2 caducan (900s). Si un ítem guardó una URL firmada
``imagen_url`` y se serializa más tarde (detalle, PDF), esa URL ya no sirve.
Este helper re-resuelve la URL actual del archivo de producto registrado en la
tabla ``archivos`` (por ``producto_id``) y solo cae al valor guardado cuando no
hay archivo público registrado o el almacenamiento no está configurado.
"""
from sqlalchemy.orm import Session

from app.models.archivo import Archivo
from app.services.storage import AlmacenNulo, obtener_storage


def url_imagen_fresca(db: Session, producto_id: int | None, imagen_url: str = "") -> str:
    if not producto_id:
        return imagen_url or ""
    # Imágenes subidas manualmente (ruta local del backend) no caducan y
    # representan una elección explícita: se conservan tal cual.
    if imagen_url.startswith("/uploads/"):
        return imagen_url or ""
    archivo = (
        db.query(Archivo)
        .filter(Archivo.entidad_tipo == "producto", Archivo.entidad_id == producto_id)
        .order_by(Archivo.created_at.desc())
        .first()
    )
    if archivo is None:
        return imagen_url or ""
    storage = obtener_storage()
    if isinstance(storage, AlmacenNulo):
        return imagen_url or ""
    return storage.url(archivo.object_key, archivo.es_publico) or imagen_url or ""