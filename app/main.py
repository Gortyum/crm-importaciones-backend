import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
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
)
from app.models.proveedor import ProveedorCategoria
from app.services.config_service import ensure_config

_UPLOAD_ENV = os.getenv("UPLOAD_DIR", "uploads")
UPLOAD_DIR = (_UPLOAD_ENV if Path(_UPLOAD_ENV).is_absolute() else PROJECT_ROOT / _UPLOAD_ENV).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]

app = FastAPI(title="CRM/ERP Cotizaciones", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clientes.router)
app.include_router(proveedores.router)
app.include_router(proveedor_categorias.router)
app.include_router(productos.router)
app.include_router(cotizaciones.router)
app.include_router(ordenes_compra.router)
app.include_router(divisas.router)
app.include_router(importaciones.router)
app.include_router(config.router)
app.include_router(upload.router)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        categorias = ["Mercancia", "Logistica", "Aduana", "Flete Terrestre Local"]
        existentes = {c.nombre for c in db.query(ProveedorCategoria).all()}
        for nombre in categorias:
            if nombre not in existentes:
                db.add(ProveedorCategoria(nombre=nombre))
        ensure_config(db)
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}
