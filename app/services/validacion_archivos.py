"""Validación compartida de archivos subidos (allowlists, tamaños, nombres).

Un único lugar para qué se acepta y cómo se nombra; el path de subida y el
path heredado de uploads comparten estas reglas.
"""
from __future__ import annotations

import re
from pathlib import PurePath

from fastapi import HTTPException

EXT_MIME: dict[str, list[str]] = {
    "jpg": ["image/jpeg"],
    "png": ["image/png"],
    "webp": ["image/webp"],
    "gif": ["image/gif"],
    "pdf": ["application/pdf", "application/octet-stream"],
}

IMG_EXT = {"jpg", "png", "webp", "gif"}
DOC_EXT = set(EXT_MIME) - IMG_EXT

MAX_IMG = 10 * 1024 * 1024
MAX_DOC = 20 * 1024 * 1024
NOMBRE_SEGURO = re.compile(r"^[\w.\- ]+$")

CARPETAS = {
    "producto": "productos",
    "cotizacion": "cotizaciones",
    "orden_compra": "ordenes-compra",
    "proveedor": "proveedores",
    "documento": "documentos",
}


def validar_extension(entidad_tipo: str, ext: str, mime: str) -> None:
    if ext not in EXT_MIME:
        raise HTTPException(400, f"Extensión .{ext} no permitida")
    if mime not in EXT_MIME[ext]:
        raise HTTPException(
            400, f"El tipo MIME {mime} no corresponde a la extensión .{ext}"
        )
    if entidad_tipo == "producto" and ext not in IMG_EXT:
        raise HTTPException(400, "Las imágenes de productos solo admiten jpg, png, webp o gif")


def limite_para(entidad_tipo: str) -> int:
    return MAX_IMG if entidad_tipo == "producto" else MAX_DOC


def carpeta_para(entidad_tipo: str) -> str:
    if entidad_tipo not in CARPETAS:
        permitidos = ", ".join(CARPETAS)
        raise HTTPException(400, f"entidad_tipo inválido: {entidad_tipo}. Usa: {permitidos}")
    return CARPETAS[entidad_tipo]


def nombre_seguro(nombre: str) -> str:
    nombre_original = PurePath(nombre or "archivo").name[:255]
    if not NOMBRE_SEGURO.match(nombre_original):
        raise HTTPException(400, "Nombre de archivo no válido")
    return nombre_original