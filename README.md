# CRM Importaciones - Backend

API para gestionar cotizaciones de productos importados. Hecha con FastAPI, SQLAlchemy y SQLite.

## Qué hace

- **Catálogos**: clientes (con contactos), proveedores, productos
- **Cotizaciones**: calcula costos desde el precio de origen (USD/BRL/CLP) hasta precio de venta final con flete, margen, descuento e IVA
- **Imágenes**: sube fotos de productos, el backend las procesa automáticamente (quita fondo con rembg, recorta, ajusta brillo/contraste, comprime a WebP)
- **Órdenes de compra**: genera OC por proveedor desde una cotización
- **Divisas**: tipo de cambio en tiempo real desde mindicador.cl

## Requisitos

- Python 3.11+
- pip

## Setup

```bash
cp .env.example .env
pip install -r requirements.txt
python -m app.seed   # carga datos de ejemplo (3 clientes, 3 proveedores, 8 productos)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La API queda en `http://localhost:8000`. La documentación interactiva en `http://localhost:8000/docs`.

## Variables de entorno

| Variable | Descripción | Default |
|---|---|---|
| `DATABASE_URL` | URL de conexión a la base de datos | `sqlite:///./crm_erp.db` |
| `UPLOAD_DIR` | Directorio donde se guardan las imágenes | `uploads` |
| `CORS_ORIGINS` | Orígenes permitidos (separados por coma) | `http://localhost:5173` |
| `HOST` | Host del servidor | `0.0.0.0` |
| `PORT` | Puerto del servidor | `8000` |

Para PostgreSQL, cambia `DATABASE_URL`:
```
DATABASE_URL=postgresql://usuario:password@localhost:5432/nombre_db
```

## Estructura

```
app/
├── main.py              # FastAPI app, CORS, startups
├── database.py          # SQLAlchemy engine y session
├── seed.py              # datos de prueba
├── models/              # modelos SQLAlchemy
│   ├── cliente.py       # Cliente + Contacto
│   ├── cotizacion.py    # Cotizacion + ItemCotizacion
│   ├── orden_compra.py  # OrdenCompra + ItemOrdenCompra
│   ├── producto.py
│   └── proveedor.py
├── schemas/             # schemas Pydantic (request/response)
├── routers/             # endpoints
│   ├── clientes.py
│   ├── cotizaciones.py  # CRUD + transiciones de estado + PDF data
│   ├── ordenes_compra.py
│   ├── productos.py
│   ├── proveedores.py
│   ├── divisas.py       # tipo de cambio
│   └── upload.py        # subida de imágenes
└── services/
    ├── cotizacion_engine.py  # lógica de cálculo (flete, margen, IVA)
    ├── divisa.py             # consulta mindicador.cl
    └── image_processor.py    # rembg + PIL (fondo blanco, crop, ajustes, WebP)
```

## Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| GET/POST | `/api/clientes/` | listar/crear clientes |
| GET/POST | `/api/proveedores/` | listar/crear proveedores |
| GET/POST | `/api/productos/` | listar/crear productos |
| GET/POST | `/api/cotizaciones/` | listar/crear cotizaciones |
| PATCH | `/api/cotizaciones/{id}/estado` | cambiar estado (Creada → Enviada → Cerrada → ...) |
| GET | `/api/cotizaciones/{id}/pdf-data` | datos para generar el PDF |
| POST | `/api/ordenes-compra/` | crear OC desde cotización + proveedor |
| POST | `/api/upload/` | subir imagen (procesada automáticamente) |
| GET | `/api/divisas/cambio` | tipo de cambio USD/BRL/EUR |

## Procesamiento de imágenes

Cuando subes una imagen, pasa por este pipeline:

1. Se guarda la original en `uploads/originals/` (privada)
2. Se elimina la metadata EXIF
3. Se quita el fondo con rembg, se reemplaza por blanco
4. Se recorta al contenido (auto-crop con padding)
5. Ajustes: brillo +5%, contraste +5%, saturación +3%, nitidez +15%
6. Se redimensiona a max 1200px
7. Se guarda como WebP al 78% de calidad

La primera subida es lenta (~10-15s) porque rembg descarga el modelo U2Net. Las siguientes toman ~2-3s.

## Notas

- La base de datos se crea automáticamente al iniciar el servidor
- El seed se puede correr múltiples veces (no duplica datos)
- Las cotizaciones tienen estados: Creada → Enviada → Cerrada → En Producción → Entregada (o Cancelada en cualquier momento)
- Las Órdenes de Compra se generan desde una cotización, filtrando items por proveedor
