"""
Punto de entrada raíz para `uvicorn main:app --reload`.

Este archivo re-exporta la aplicación FastAPI que vive en `app/main.py`,
para que puedas levantar el servidor desde la raíz del proyecto con:

    uvicorn main:app --reload

La construcción del paquete `app` se resuelve automáticamente porque
este archivo se ejecuta desde el directorio del proyecto.
"""
from app.main import app  # noqa: F401

__all__ = ["app"]
