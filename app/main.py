import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base, SessionLocal
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
    documentos,
)
from app.routers.auth import requiere_autenticacion
from app.models.proveedor import ProveedorCategoria
from app.services.config_service import ensure_config
from app.services.demo_data import asegurar_bd_demo
from app.services.image_processor import UPLOAD_DIR

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
app.include_router(documentos.router, dependencies=[Depends(requiere_autenticacion)])

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    _migrar_columnas()
    try:
        asegurar_bd_demo()
    except Exception as exc:  # la demo nunca debe tumbar la aplicación real
        print(f"[demo] No se pudo preparar la base demo: {type(exc).__name__}")
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
    if "cotizaciones" in insp.get_table_names():
        columnas = {c["name"] for c in insp.get_columns("cotizaciones")}
        if "pdf_emitido" not in columnas:
            # PG exige boolean literal; SQLite acepta 0/1.
            default_expr = "FALSE" if engine.dialect.name == "postgresql" else "0"
            with engine.begin() as conn:
                conn.execute(text(
                    f"ALTER TABLE cotizaciones ADD COLUMN pdf_emitido BOOLEAN DEFAULT {default_expr}"
                ))
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
    if "archivos" in insp.get_table_names():
        columnas = {c["name"] for c in insp.get_columns("archivos")}
        if "hash_sha256" not in columnas:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE archivos ADD COLUMN hash_sha256 VARCHAR(64)"))
        if engine.dialect.name == "sqlite":
            # SQLite no permite eliminar índices UNIQUE de constraints; si la tabla
            # está vacía (dev), se reconstruye sin el unique para habilitar el dedup.
            with engine.connect() as conn:
                count = conn.execute(text("SELECT COUNT(*) FROM archivos")).scalar()
            if count == 0:
                with engine.begin() as conn:
                    conn.execute(text("DROP TABLE archivos"))
                from app.models.archivo import Archivo  # noqa: F401

                Archivo.__table__.create(bind=engine, checkfirst=True)
        else:
            with engine.begin() as conn:
                conn.execute(text("DROP INDEX IF EXISTS ix_archivos_object_key"))
                conn.execute(text("ALTER TABLE archivos DROP CONSTRAINT IF EXISTS archivos_object_key_key"))


@app.get("/api/health")
def health():
    return {"status": "ok"}
