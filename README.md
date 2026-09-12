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
| `ALLOWED_ORIGINS` | Orígenes permitidos por CORS (separados por coma) | `http://localhost:5173` |
| `HOST` | Host del servidor | `0.0.0.0` |
| `PORT` | Puerto del servidor | `8000` |

> En producción, `ALLOWED_ORIGINS` debe listar el origin del frontend (donde corre
> React), p. ej. `http://localhost:5173,https://crm-importaciones-frontend-pi.vercel.app`.
> El backend NO debe ir en esa lista (es el que recibe las peticiones, no el que las origina).

Para PostgreSQL, cambia `DATABASE_URL`:
```
DATABASE_URL=postgresql://usuario:password@localhost:5432/nombre_db
```

## Almacenamiento de archivos (Cloudflare R2)

Archivos e imágenes se guardan en un bucket de **Cloudflare R2** (API compatible con S3).
PostgreSQL solo guarda metadatos (tabla `archivos`); nunca el contenido.

### Variables de entorno

| Variable | Descripción | Obligatoria |
|---|---|---|
| `R2_ACCOUNT_ID` | ID de cuenta de Cloudflare | Sí (para armar el endpoint por defecto) |
| `R2_ACCESS_KEY_ID` | Token R2 (Access Key ID) | Sí |
| `R2_SECRET_ACCESS_KEY` | Token R2 (Secret Access Key) | Sí |
| `R2_BUCKET_NAME` | Nombre del bucket | Sí |
| `R2_ENDPOINT` | URL S3-compatible (default: `https://<account>.r2.cloudflarestorage.com`) | No |
| `R2_PUBLIC_URL` | URL pública del bucket para archivos públicos (imágenes de productos) | No |

Sin estas variables, `/api/archivos/*` responde `503` con mensaje claro y el flujo local
(`/api/upload/` + `/uploads`) sigue operando para desarrollo.

### Configuración en Cloudflare

1. Crear el bucket (nombre = `R2_BUCKET_NAME`).
2. Crear un **token de API** en R2 con permiso **Object Read & Write**; copiar Access Key ID
   y Secret Access Key.
3. (Opcional) Vincular un dominio personalizado o activar el acceso público del bucket y usar
   esa URL como `R2_PUBLIC_URL`. Sin dominio público, las imágenes se sirven igual por URL firmada.

### CORS del bucket (necesario para el PDF)

El PDF se genera en el navegador con `html2canvas`, que hace `fetch` de las imágenes → el bucket
debe permitir `GET` desde el origin del frontend. En Cloudflare → R2 → bucket → **Settings →
CORS Policy**, agrega:

```json
[
  {
    "AllowedOrigins": ["https://crm-importaciones-frontend-pi.vercel.app", "http://localhost:5173"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["Content-Length", "Content-Type"],
    "MaxAgeSeconds": 3600
  }
]
```

### Organización y detección de duplicados

- Rutas dentro del bucket: `productos/`, `cotizaciones/`, `ordenes-compra/`, `proveedores/`, `documentos/`.
- Imágenes de productos (públicas) se muestran directamente desde React y entran al PDF.
- Documentos (privados) se descargan con **URL firmada** (`GET /api/archivos/{id}/descargar`),
  que valida el JWT y expira en 15 minutos.
- **Dedup por SHA-256**: si el contenido ya existe, se reutiliza el objeto físico (una sola copia)
  y solo se crea una referencia nueva. Al borrar, el objeto se elimina únicamente cuando no quedan
  referencias.

### Endpoints de archivos

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/archivos/upload` | Subir archivo (valida extensión/MIME/tamaño/nombre) |
| GET | `/api/archivos/?entidad_tipo=&entidad_id=` | Listar adjuntos de una entidad |
| GET | `/api/archivos/{id}` | Metadatos + URL (pública o firmada) |
| GET | `/api/archivos/{id}/descargar` | Redirige a URL firmada temporal (requiere JWT) |
| DELETE | `/api/archivos/{id}` | Eliminar (con conteo de referencias) |

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
│   ├── upload.py        # subida de imágenes (fallback local)
│   └── archivos.py      # archivos en Cloudflare R2 (subir/listar/descargar/eliminar)
└── services/
    ├── cotizacion_engine.py  # lógica de cálculo (flete, margen, IVA)
    ├── divisa.py             # consulta mindicador.cl / open.er-api.com
    ├── image_processor.py    # rembg + PIL (fondo blanco, crop, ajustes, WebP)
    ├── cache.py              # Redis con fallback en memoria
    ├── referencias.py        # referencias del login
    └── storage.py            # cliente Cloudflare R2 (S3-compatible)
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
