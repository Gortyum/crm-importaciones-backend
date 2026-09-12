# CRM Eleni Sourcing — Backend (API REST)

Backend para el CRM de **Eleni Sourcing · Importaciones**. Expone una API REST usada por el
frontend React (`crm-importaciones-frontend`) para gestionar clientes, proveedores, productos,
**cotizaciones**, **importaciones** y **órdenes de compra** de mercancía entre Brasil y Chile.

---

## 1. Stack

- **Python 3.11** · **FastAPI** · Uvicorn
- **SQLAlchemy** (ORM) + **SQLite** en desarrollo / **PostgreSQL** en producción (Railway)
- **PyJWT** para autenticación (Bearer token)
- **Redis** opcional como caché de referencias (con **fallback en memoria**)
- **Pillow** para procesamiento de imágenes
- **boto3** para el bucket **Cloudflare R2** (archivos adjuntos)

## 2. Estructura del proyecto

```
app/
├── main.py                 # App, CORS, routers, migraciones idempotentes
├── security.py             # JWT (hash de contraseñas, token, dependencia de autenticación)
├── database.py             # engine, SessionLocal, Base
├── models/
│   ├── usuario.py          # usuarios (username, password_hash, rol)
│   ├── cliente.py          # clientes + contactos_clientes
│   ├── proveedor.py        # proveedores + proveedor_categorias
│   ├── producto.py         # productos
│   ├── cotizacion.py       # cotizaciones + items_cotizacion
│   ├── importacion.py      # importaciones + items_importacion + costos_importacion
│   ├── orden_compra.py     # ordenes_compra + items_orden_compra
│   ├── configuracion.py    # parametros globales (IVA, aranceles)
│   ├── archivo.py          # metadatos de archivos en R2 (tabla archivos)
│   └── enums.py            # estados y tipos (Divisa, TipoFlete, TipoPersonalizacion, ...)
├── routers/                # Endpoints por recurso (ver sección 7)
├── schemas/                # Pydantic (request/response)
└── services/
    ├── auth_service.py         # bcrypt + JWT
    ├── cotizacion_engine.py    # cálculo de cotización (flete, margen, IVA)
    ├── importacion_engine.py   # cálculo de importación (FOB → CIF → landed cost)
    ├── divisa.py               # tipo de cambio (mindicador.cl + open.er-api.com)
    ├── config_service.py       # lectura de configuración global
    ├── referencias.py          # catálogos, estados y TC devueltos al iniciar sesión
    ├── cache.py                # Redis con fallback en memoria
    ├── image_processor.py      # pipeline de imágenes (EXIF, ajustes, resize → WebP)
    └── storage.py              # cliente Cloudflare R2 (S3-compatible)
```

## 3. Puesta en marcha (desarrollo local)

```bash
# 1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate      # Linux/macOS

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Variables de entorno (copiar y completar)
copy .env.example .env          # Windows
# cp .env.example .env          # Linux/macOS

# 4. Levantar el servidor
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- Documentación interactiva: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`
- Al arrancar se crean las tablas (si no existen) y la configuración por defecto
  (IVA 19%, arancel general 6%, arancel Mercosur 0%).
- Para el primer login usa `POST /api/auth/register` (endpoint temporal) o ejecuta
  `python -m app.seed` para cargar clientes, proveedores y productos de ejemplo
  (no crea usuarios).

## 4. Variables de entorno

| Variable | Descripción | Default |
|---|---|---|
| `DATABASE_URL` | Conexión a la base de datos | `sqlite:///./crm_erp.db` |
| `SECRET_KEY` | Clave para firmar JWT | `secret-key-cambiar-en-produccion` |
| `UPLOAD_DIR` | Directorio de imágenes (fallback local) | `uploads` |
| `ALLOWED_ORIGINS` | Orígenes permitidos por CORS (separados por coma) | `http://localhost:5173` |
| `REDIS_URL` | Caché de referencias (opcional; si falla usa memoria) | — |
| `HOST` / `PORT` | Host y puerto del server | `0.0.0.0` / `8000` |
| `R2_ACCOUNT_ID` | ID de cuenta Cloudflare (R2) | — |
| `R2_ACCESS_KEY_ID` | Token R2 (Access Key ID) | — |
| `R2_SECRET_ACCESS_KEY` | Token R2 (Secret Access Key) | — |
| `R2_BUCKET_NAME` | Nombre del bucket R2 | — |
| `R2_ENDPOINT` | URL S3-compatible (default: `https://<account>.r2.cloudflarestorage.com`) | — |
| `R2_PUBLIC_URL` | URL pública del bucket (imágenes públicas de productos) | — |

### CORS

`ALLOWED_ORIGINS` debe listar el/los **origin del frontend** (donde corre React), no el del backend:

```
ALLOWED_ORIGINS=http://localhost:5173,https://crm-importaciones-frontend-pi.vercel.app
```

Sin esas variables R2, los endpoints `/api/archivos/*` responden `503` con un mensaje claro y el
flujo local (`/api/upload/` + `/uploads`) sigue operando para desarrollo.

## 5. Autenticación y referencias

- **Login**: `POST /api/auth/login` → devuelve `access_token`, `username` y las **referencias**.
- **Registro (temporal)**: `POST /api/auth/register` sirve para crear el primer administrador.
  Está marcado como provisional en el código («se retira cuando se indique»); en producción
  conviene quitarlo o bloquearlo por red cuando el primer usuario exista.
- `GET /api/auth/me` → datos del usuario autenticado.
- `GET /api/auth/referencias` → catálogos y constantes del negocio:

| Campo | Contenido |
|---|---|
| `usuario` / `permisos` | Usuario actual y módulos autorizados por rol |
| `monedas` | Tipo de cambio del día (USD, EUR, BRL, CLP=1) |
| `tc_cotizacion` | TC con el % de contingencia aplicado, para cotizar |
| `seguridad_pct` | % de contingencia configurado |
| `config` | `iva_chile`, `arancel_general`, `arancel_mercosur` |
| `estados` | Estados y transiciones de cotización, importación y OC |
| `categorias_productos` | Categorías de proveedores (catálogo) |
| `fecha_tc` | Fecha de los tipos de cambio |

Las referencias se cachean vía `app/services/cache.py` (Redis si `REDIS_URL` existe, con fallback
en memoria) con **TTL de 10 minutos**; si el TC quedara viejo, basta reiniciar o limpiar el caché,
y `refreshReferencias` del frontend las vuelve a pedir sin re-loguear.

## 6. Base de datos y migraciones

**SQLite** (dev): archivo `crm_erp.db` en la raíz. **PostgreSQL** (prod): controlado por `DATABASE_URL`.

Tablas principales:

- `usuarios`
- `clientes` + `contactos_clientes`
- `proveedores` + `proveedor_categorias`
- `productos`
- `cotizaciones` + `items_cotizacion`
- `importaciones` + `items_importacion` + `costos_importacion`
- `ordenes_compra` + `items_orden_compra`
- `configuracion`
- `archivos`

**Migraciones**: se ejecutan automáticamente en `app/main.py` al arrancar y son idempotentes
(`_migrar_columnas`):

- Añade `tipo_cambio` a `items_cotizacion` (si no existe).
- Añade `rol` a `usuarios` (si no existe).
- Añade `hash_sha256` a `archivos` (si no existe).
- Elimina la **restricción UNIQUE** de `object_key` en `archivos` (SQLite: reconstruye la tabla solo
  si está vacía; PostgreSQL: `DROP INDEX` / `DROP CONSTRAINT` ignorando errores) — necesaria para
  permitir **dedup**: varias referencias pueden apuntar al mismo archivo físico.

## 7. Endpoints

| Área | Método | Ruta |
|---|---|---|
| Salud | GET | `/api/health` |
| Auth | POST | `/api/auth/login` |
| Auth | POST | `/api/auth/register` (temporal) |
| Auth | GET | `/api/auth/me`, `/api/auth/referencias` |
| Auth | PUT | `/api/auth/cambiar-password` |
| Config | GET/PUT | `/api/config/` (IVA, aranceles, contingencia) |
| Clientes | CRUD | `/api/clientes/` + `/api/clientes/{id}/contactos/` |
| Proveedores | CRUD | `/api/proveedores/` |
| Categorías | CRUD | `/api/proveedor-categorias/` |
| Productos | CRUD | `/api/productos/` |
| Cotizaciones | CRUD | `/api/cotizaciones/` |
| Cotizaciones | PATCH | `/api/cotizaciones/{id}/estado` |
| Cotizaciones | POST | `/api/cotizaciones/{id}/crear-importacion` |
| Cotizaciones | GET | `/api/cotizaciones/{id}/pdf-data` |
| Importaciones | CRUD | `/api/importaciones/` |
| Importaciones | PATCH | `/api/importaciones/{id}/estado` |
| Importaciones | POST | `/api/importaciones/{id}/pasar-a-cotizacion` |
| Importaciones | POST | `/api/importaciones/{id}/calcular` (preview) |
| OCs | CRUD | `/api/ordenes-compra/` |
| OCs | PATCH | `/api/ordenes-compra/{id}/estado` |
| OCs | GET | `/api/ordenes-compra/{id}/pdf-data` |
| Divisas | GET | `/api/divisas/cambio` |
| Imágenes | POST | `/api/upload/` (fallback local) |
| Archivos | POST | `/api/archivos/upload` |
| Archivos | GET | `/api/archivos/?entidad_tipo=&entidad_id=` |
| Archivos | GET | `/api/archivos/{id}`, `/api/archivos/{id}/descargar` |
| Archivos | DELETE | `/api/archivos/{id}` |

Todas las rutas de negocio requieren header `Authorization: Bearer <token>`.

## 8. Estados y transiciones

**Cotización**: `Creada → Enviada → Cerrada → En Produccion → Entregada` (+ `Cancelada` desde
Creada/Enviada/Cerrada/En Produccion).

**Importación**: `Borrador → En Transito → En Bodega → Cerrada` (+ `Cancelada` desde las tres
primeras).

**Orden de compra**: `Pendiente → Confirmada → En Produccion → Recibida` (+ `Cancelada`).

## 9. Cálculos de negocio

### Cotización (`cotizacion_engine.py`)

- El **tipo de cambio** vive en cada item (`tipo_cambio`) y corresponde a su divisa de origen
  (cuántos CLP vale 1 unidad; `1.0` si la divisa es CLP).
- **Flete**: si `costo_flete` manual > 0 se usa tal cual (CLP); si no, se estima por tarifa por kg
  o por m³ según tipo de transporte (Aéreo/Terrestre/Marítimo) y se usa el mayor:

  | Transporte | Tarifa por kg | Tarifa por m³ |
  |---|---|---|
  | Aéreo | $4.500 | $35.000 |
  | Terrestre | $1.800 | $12.000 |
  | Marítimo | $900 | $5.000 |

- El flete es el costo **total del lote** (no por unidad): se suma una sola vez.
- `subtotal = (costo + envío) × cantidad + flete` → se aplica margen → se aplica descuento →
  IVA → total. El precio unitario = total neto ÷ cantidad.
- Se guarda también `tipo_cambio` en el item para que el PDF y el detalle reproduzcan el cálculo.

### Importación (`importacion_engine.py`)

Modelo **FOB → CIF → arancel → contingencia → landed cost → precio de venta**:

1. Cada item: precio de fábrica convertido a USD → `fob` = precio × cantidad.
2. Costos según transporte (Courier / Aéreo / Terrestre): flete internacional, seguro, gastos de
   despacho, honorarios de agente y flete local, cada uno en su divisa.
3. `cif = fob + flete + seguro`; **arancel** sobre CIF (6% general, 0% Mercosur con certificado de
   origen).
4. **Contingencia** (% configurado) sobre `cif + gastos extranjeros no CIF`.
5. **IVA de importación** sobre `(cif + arancel)`.
6. `costo_almacén` (CLP) repartido entre items proporcional al FOB → cada item obtiene
   `costo_unitario_neto`, y con el margen se calcula `precio_venta` (neto + IVA).

### Divisas (`divisa.py`)

- Consulta **mindicador.cl** (USD y EUR frente al CLP) y **open.er-api.com** (`https://open.er-api.com/v6/latest/USD`,
  tasa BRL/USD) en paralelo con `asyncio.gather`.
- `BRL → CLP` = `USD/CLP ÷ BRL/USD`.
- Fallbacks en cadena: EUR/6.05 si falta BRL; y un fallback global `{USD: 950, EUR: 1025, BRL: 180}`
  si la API externa no responde (para que app nunca falle por el mercado).
- Nota: el endpoint `mindicador.cl/api/real` **no existe** («No se ha encontrado el indicador
  económico»); el real no se consulta.

## 10. Imágenes y archivos

### Pipeline local (fallback) — `/api/upload/`

`POST /api/upload/` recibe una imagen multipart y valida: MIME debe ser `image/jpeg|png|webp|gif`
y tamaño ≤ 10 MB. Luego `process_image` (`app/services/image_processor.py`):

1. Guarda el **original** (UUID.ext) en `uploads/originals/`.
2. Procesa con PIL: elimina metadatos EXIF, ajusta brillo/contraste/color/nitidez,
   redimensiona a 1200 px máximo (LANCZOS) y guarda como **WebP** (calidad 78) en `uploads/`.
3. Devuelve `{ url: "/uploads/<uuid>.webp", filename, original_filename }`.

La imagen se sirve en `/uploads/{archivo}`. En producción el almacenamiento primario es
Cloudflare R2; `/api/upload/` queda como respaldo para desarrollo.

### Cloudflare R2 — `/api/archivos/*`

| Variable | Descripción | Obligatoria |
|---|---|---|
| `R2_ACCOUNT_ID` | ID de cuenta de Cloudflare | Sí (para el endpoint por defecto) |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | Token con permiso **Object Read & Write** | Sí |
| `R2_BUCKET_NAME` | Nombre del bucket | Sí |
| `R2_ENDPOINT` | URL S3-compatible | No |
| `R2_PUBLIC_URL` | URL pública del bucket | No |

**Pasos en Cloudflare**:

1. Crear el bucket (nombre = `R2_BUCKET_NAME`).
2. R2 → **Administrar tokens de API del bucket** → Crear token → **Object Read & Write**.
3. (Opcional) Dominio personalizado o acceso público para `R2_PUBLIC_URL`.

**Organización** (carpetas por entidad): `productos/`, `cotizaciones/`, `ordenes-compra/`,
`proveedores/`, `documentos/`.

- Las **imágenes de productos** son públicas (se muestran directo desde React y entran al PDF).
- Los **documentos** son privados: se descargan con **URL firmada** (`GET /api/archivos/{id}/descargar`),
  que valida el JWT y expira en 15 minutos.

**Validaciones de subida** (`POST /api/archivos/upload`):

- Extensiones: `jpg jpeg png webp gif pdf doc docx xls xlsx csv txt`.
- El **MIME debe corresponder** a la extensión (ej: enviar un `.txt` como `image/png` → 400).
- Máximo **10 MB** imágenes / **20 MB** documentos.
- El object key es un UUID generado por el backend; el nombre original se guarda saneado.
- `es_publico` solo se permite para la carpeta `producto`; el resto se fuerza privado.

**Dedup por SHA-256**: el backend calcula el hash del contenido. Si el archivo ya existe en el
bucket, se **reutiliza el objeto** (no se sube de nuevo) y solo se crea la referencia nueva;
la respuesta lo indica con `duplicado: true`. Al borrar, el objeto R2 se elimina únicamente cuando
no queda ninguna otra fila con el mismo `object_key` (refcount).

**CORS del bucket (necesario para el PDF)**: el PDF se genera en el navegador con `html2canvas`,
que carga las imágenes por `fetch` → el bucket debe permitir `GET` desde el origin del frontend.
En Cloudflare → R2 → bucket → **Settings → CORS Policy**:

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

## 11. Despliegue (Railway + PostgreSQL)

1. Crear servicio con este repositorio (buildpack de Python).
2. Variables en Railway:
   ```
   DATABASE_URL=postgresql://<user>:<pass>@<host>:5432/<db>
   SECRET_KEY=<valor-largo-y-aleatorio>
   ALLOWED_ORIGINS=http://localhost:5173,https://crm-importaciones-frontend-pi.vercel.app
   REDIS_URL=<opcional>
   R2_ACCOUNT_ID=<...>
   R2_ACCESS_KEY_ID=<...>
   R2_SECRET_ACCESS_KEY=<...>
   R2_BUCKET_NAME=<...>
   ```
3. Al desplegar se ejecuta el comando de arranque del servicio; verifica que apunte a `main:app`,
   por ejemplo: `uvicorn main:app --host 0.0.0.0 --port ${PORT}` (Railway provee `PORT`).
4. La API queda en `https://crm-importaciones-backend-production.up.railway.app`. Verificar:
   `GET /api/health` → 200.

> El backend solo sirve la API: `GET /` responde 404 en producción. El frontend corre en un
> dominio aparte (Vercel) y apunta a esta URL vía `VITE_API_URL`.

---

## Notas de desarrollo

- Cómo crear el primer usuario: `POST /api/auth/register` (temporal; retirar en producción).
- Datos de ejemplo (clientes/proveedores/productos): `python -m app.seed` — no crea usuarios.
- No hay archivos de secretos en el repo: todo vive en `.env` (local) o en las variables de Railway.