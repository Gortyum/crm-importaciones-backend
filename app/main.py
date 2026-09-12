import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base, SessionLocal, PROJECT_ROOT
from app.routers import (
    clientes,
    proveedores,
    proveedor_categorias,
    productos,
    cotizaciones,
    divisas,
    ordenes_compra,
    importaciones,
    config,
    upload,
    archivos,
    auth,
)
from app.routers.auth import requiere_autenticacion
from app.models.proveedor import ProveedorCategoria
from app.services.config_service import ensure_config

_UPLOAD_ENV = os.getenv("UPLOAD_DIR", "uploads")
UPLOAD_DIR = (_UPLOAD_ENV if Path(_UPLOAD_ENV).is_absolute() else PROJECT_ROOT / _UPLOAD_ENV).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")]

app = FastAPI(title="CRM/ERP Cotizaciones", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas publicas: login (autenticarse) y health solo no exigen token.
# Todo el resto de la API de negocio queda protegida por JWT.
app.include_router(auth.router)

app.include_router(clientes.router, dependencies=[Depends(requiere_autenticacion)])
app.include_router(proveedores.router, dependencies=[Depends(requiere_autenticacion)])
app.include_router(proveedor_categorias.router, dependencies=[Depends(requiere_autenticacion)])
app.include_router(productos.router, dependencies=[Depends(requiere_autenticacion)])
app.include_router(cotizaciones.router, dependencies=[Depends(requiere_autenticacion)])
app.include_router(ordenes_compra.router, dependencies=[Depends(requiere_autenticacion)])
app.include_router(divisas.router, dependencies=[Depends(requiere_autenticacion)])
app.include_router(importaciones.router, dependencies=[Depends(requiere_autenticacion)])
app.include_router(config.router, dependencies=[Depends(requiere_autenticacion)])
app.include_router(upload.router, dependencies=[Depends(requiere_autenticacion)])
app.include_router(archivos.router, dependencies=[Depends(requiere_autenticacion)])

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    _migrar_columnas()
    db = SessionLocal()
    try:
        categorias = ["Mercancia", "Logistica", "Aduana", "Flete Terrestre Local"]
        existentes = {c.nombre for c in db.query(ProveedorCategoria).all()}
        for nombre in categorias:
            if nombre not in existentes:
                db.add(ProveedorCategoria(nombre=nombre))
        ensure_config(db)
        db.commit()
    finally:
        db.close()


def _migrar_columnas():
    from sqlalchemy import text, inspect

    insp = inspect(engine)
    if "items_cotizacion" in insp.get_table_names():
        columnas = {c["name"] for c in insp.get_columns("items_cotizacion")}
        if "tipo_cambio" not in columnas:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE items_cotizacion ADD COLUMN tipo_cambio FLOAT DEFAULT 1.0"))
                conn.execute(text("UPDATE items_cotizacion SET tipo_cambio = 1.0 WHERE tipo_cambio IS NULL"))
    if "usuarios" in insp.get_table_names():
        columnas = {c["name"] for c in insp.get_columns("usuarios")}
        if "rol" not in columnas:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN rol VARCHAR(30) DEFAULT 'admin'"))
                conn.execute(text("UPDATE usuarios SET rol = 'admin' WHERE rol IS NULL"))


@app.get("/api/health")
def health():
    return {"status": "ok"}
