"""Datos sintéticos del modo demo, sembrados en una base de datos aislada.

Todo este módulo opera únicamente contra ``demo_engine``: la base demo
(normalmente ``crm_erp_demo.db`` en desarrollo o ``DEMO_DATABASE_URL`` en
producción) nunca comparte tablas ni filas con la base real de la aplicación.
"""
from __future__ import annotations

from datetime import datetime

from app.database import Base, DemoSessionLocal, demo_engine
from app.models.cliente import Cliente, Contacto
from app.models.configuracion import ConfigGlobal
from app.models.cotizacion import Cotizacion, ItemCotizacion
from app.models.documento import Documento
from app.models.importacion import (
    Importacion,
    ImportacionCosto,
    ImportacionItem,
    ImportacionProveedor,
)
from app.models.orden_compra import ItemOrdenCompra, OrdenCompra
from app.models.producto import Producto
from app.models.proveedor import Proveedor, ProveedorCategoria
from app.models.usuario import Usuario
from app.schemas.cotizacion import ItemCotizacionCreate
from app.services.auth_service import hash_password
from app.services.config_service import DEFAULTS
from app.services.cotizacion_engine import calcular_item
from app.services.importacion_engine import calcular_importacion

USUARIO_DEMO = "demo"
USUARIO_DEMO_PASSWORD = "demo1234"

ANIO = datetime.now().year
TC_USD_CLP = 930.0

CATEGORIAS = ["Mercancia", "Logistica", "Aduana", "Flete Terrestre Local"]

CLIENTES = [
    {
        "razon_social": "Comercial Cortés SpA",
        "rut": "77.111.222-3",
        "direccion": "Av. Providencia 2201, Providencia",
        "giro": "Vestuario corporativo",
        "contactos": [
            {"nombre": "Daniela Cortés", "cargo": "Gerente General", "email": "dcortes@comercialcortes.cl", "telefono": "+56951234567", "es_principal": True},
            {"nombre": "Felipe Rojas", "cargo": "Jefe de Compras", "email": "frojas@comercialcortes.cl", "telefono": "+56998765432", "es_principal": False},
        ],
    },
    {
        "razon_social": "Minera Alto Pacífico Ltda",
        "rut": "76.555.444-2",
        "direccion": "Av. Argentina 1580, Antofagasta",
        "giro": "Minería",
        "contactos": [
            {"nombre": "Jorge Atala", "cargo": "Superintendente de Abastecimiento", "email": "jatala@altopacifico.cl", "telefono": "+56955667788", "es_principal": True},
        ],
    },
    {
        "razon_social": "Supermercados del Valle SA",
        "rut": "97.333.222-1",
        "direccion": "Av. Libertador Bernardo O'Higgins 940, Rancagua",
        "giro": "Retail",
        "contactos": [
            {"nombre": "Camila Sandoval", "cargo": "Encargada Marketing", "email": "csandoval@superdelvalle.cl", "telefono": "+56922334455", "es_principal": True},
        ],
    },
    {
        "razon_social": "Clínica Los Robles",
        "rut": "78.444.555-6",
        "direccion": "Av. La Dehesa 1200, Lo Barnechea",
        "giro": "Salud",
        "contactos": [
            {"nombre": "Rodrigo Menéndez", "cargo": "Administrador", "email": "rmenendez@clinicalosrobles.cl", "telefono": "+56933445566", "es_principal": True},
        ],
    },
    {
        "razon_social": "Agencia Aventura Austral",
        "rut": "76.888.999-4",
        "direccion": "Km 3,5 Camino a Ensenada, Puerto Varas",
        "giro": "Turismo",
        "contactos": [
            {"nombre": "Valentina Küster", "cargo": "Fundadora", "email": "vkuster@aventuraaustral.cl", "telefono": "+56944556677", "es_principal": True},
        ],
    },
    {
        "razon_social": "Estudio Nodo Arquitectura",
        "rut": "77.222.111-5",
        "direccion": "Merced 386, Santiago Centro",
        "giro": "Arquitectura",
        "contactos": [
            {"nombre": "Ignacio Barra", "cargo": "Socio", "email": "ibarra@estudionodo.cl", "telefono": "+56966778899", "es_principal": True},
        ],
    },
]

PROVEEDORES = [
    {
        "razon_social": "Shenzhen Happen Industrial Co., Ltd.",
        "tax_id": "CN-91440300MA5G",
        "pais_origen": "China",
        "etiquetas_productos": ["Poleras", "Gorra", "Bordado"],
        "categoria": "Mercancia",
    },
    {
        "razon_social": "Dhaka Apparel Export House",
        "tax_id": "BD-004565321",
        "pais_origen": "Bangladesh",
        "etiquetas_productos": ["Polos", "Chaqueta", "DTF"],
        "categoria": "Mercancia",
    },
    {
        "razon_social": "Lima Textiles Group SAC",
        "tax_id": "PE-20601234567",
        "pais_origen": "Perú",
        "etiquetas_productos": ["Poleras Algodón", "Sublimación"],
        "categoria": "Mercancia",
    },
    {
        "razon_social": "São Paulo Print Hub",
        "tax_id": "BR-45.678.901/0001-23",
        "pais_origen": "Brasil",
        "etiquetas_productos": ["Serigrafia", "Full Print", "Tote Bag"],
        "categoria": "Mercancia",
    },
    {
        "razon_social": "Valparaíso Cargo & Aduana",
        "tax_id": "CL-76.900.001-9",
        "pais_origen": "Chile",
        "etiquetas_productos": [],
        "categoria": "Logistica",
    },
]

PRODUCTOS = [
    {"nombre": "Polera Manga Corta Cotton", "descripcion": "Polera unicolor 100% algodón peinado, tallas S-XXL", "unidad": "Unidad"},
    {"nombre": "Polo Piqué Ejecutivo", "descripcion": "Polo piqué con cuello y puños, bordado de logo", "unidad": "Unidad"},
    {"nombre": "Gorra Trucker 5 Paneles", "descripcion": "Gorra trucker mesh 5 paneles, cierre con clip", "unidad": "Unidad"},
    {"nombre": "Chaqueta Softshell Impermeable", "descripcion": "Chaqueta softshell 3 capas, zipper, bordable", "unidad": "Unidad"},
    {"nombre": "Tote Bag Canvas Reforzado", "descripcion": "Bolsa canvas 12oz con bolsillo y asas largas", "unidad": "Unidad"},
    {"nombre": "Llavero Acrílico Personalizado", "descripcion": "Llavero acrílico 4x6 cm con impresión full print", "unidad": "Unidad"},
    {"nombre": "Bolso Deportivo Cuerda", "descripcion": "Bolso tipo saco con cuerdas, poliéster 600D", "unidad": "Unidad"},
    {"nombre": "Bandana Multiuso", "descripcion": "Bandana poliéster multicoste, sublimable", "unidad": "Unidad"},
]

# Items de cotizaciones: (producto_idx, proveedor_idx, cantidad, costo, divisa, margen, personalizacion)
COTIZACION_1 = {
    "cliente_idx": 0,
    "estado": "Enviada",
    "notas": "Cotización de vestuario corporativo para el equipo comercial.",
    "items": [
        (0, 0, 120, 3.4, 35, "Bordado"),
        (1, 1, 60, 5.8, 35, "DTF"),
        (3, 1, 40, 12.5, 40, "Bordado"),
    ],
}

COTIZACION_2 = {
    "cliente_idx": 2,
    "estado": "Creada",
    "notas": "Merchandising para campaña de apertura de locales.",
    "items": [
        (4, 3, 250, 1.9, 40, "Full Print"),
        (7, 3, 400, 0.75, 45, "Sublimacion"),
    ],
}


def asegurar_bd_demo() -> DemoSessionLocal:
    """Crea las tablas y siembra los datos demo si aún no existen.

    Devuelve una sesión abierta sobre la base demo para que el endpoint
    de login construya las referencias.
    """
    Base.metadata.create_all(bind=demo_engine)
    with DemoSessionLocal() as db:
        _sembrar(db)
        db.commit()
    return DemoSessionLocal()


def _sembrar(db: DemoSessionLocal) -> None:
    if db.query(Usuario).filter(Usuario.username == USUARIO_DEMO).first():
        return

    # Usuario demo
    usuario = Usuario(
        username=USUARIO_DEMO,
        password_hash=hash_password(USUARIO_DEMO_PASSWORD),
        rol="admin",
    )
    db.add(usuario)

    # Configuración global
    for clave, valor in DEFAULTS.items():
        db.add(ConfigGlobal(clave=clave, valor=valor, etiqueta=clave))

    # Categorías de proveedores
    categorias = {}
    for nombre in CATEGORIAS:
        cat = ProveedorCategoria(nombre=nombre)
        db.add(cat)
        categorias[nombre] = cat
    db.flush()

    # Clientes + contactos
    cliente_rows = []
    for c in CLIENTES:
        cli = Cliente(
            razon_social=c["razon_social"],
            rut=c["rut"],
            direccion=c["direccion"],
            giro=c["giro"],
        )
        db.add(cli)
        cliente_rows.append((cli, c["contactos"]))

    # Proveedores
    proveedor_rows = []
    for p in PROVEEDORES:
        prov = Proveedor(
            razon_social=p["razon_social"],
            tax_id=p["tax_id"],
            pais_origen=p["pais_origen"],
            etiquetas_productos=p["etiquetas_productos"],
            categoria_id=categorias[p["categoria"]].id or None,
        )
        db.add(prov)
        proveedor_rows.append(prov)

    # Productos
    producto_rows = []
    for p in PRODUCTOS:
        prod = Producto(nombre=p["nombre"], descripcion=p["descripcion"], unidad=p["unidad"])
        db.add(prod)
        producto_rows.append(prod)

    db.flush()  # asigna ids

    # Vinculación de contactos (necesita ids de clientes)
    for cli, contactos in cliente_rows:
        for ct in contactos:
            db.add(Contacto(
                cliente_id=cli.id,
                nombre=ct["nombre"],
                cargo=ct["cargo"],
                email=ct["email"],
                telefono=ct["telefono"],
                es_principal=ct["es_principal"],
            ))

    # Cotizaciones
    cot1, _ = _seed_cotizacion(db, COTIZACION_1, cliente_rows, producto_rows, proveedor_rows, 1)
    cot2, cot2_items = _seed_cotizacion(db, COTIZACION_2, cliente_rows, producto_rows, proveedor_rows, 2)

    # Importación vinculada a la primera cotización
    _seed_importacion(db, cot1, producto_rows, proveedor_rows)

    # Orden de compra vinculada a la segunda cotización (proveedor 4 = índice 3)
    _seed_orden_compra(db, cot2, cot2_items, proveedor_rows[3])

    # Documento PDF demo sobre la primera cotización
    db.add(Documento(
        correlativo="PDF 1",
        cotizacion_id=cot1.id,
        especificaciones={
            "material": "Algodón peinado 220 g/m²",
            "personalizacion": "Bordado 2 colores (pecho)",
            "color": "Azul marino / Blanco",
            "medida_logo": "10 x 7 cm",
        },
        created_by=USUARIO_DEMO,
    ))


def _seed_cotizacion(db, spec, cliente_rows, producto_rows, proveedor_rows, numero) -> tuple:
    cli = cliente_rows[spec["cliente_idx"]][0]
    cot = Cotizacion(
        correlativo=f"COT-{ANIO}-{numero:04d}",
        cliente_id=cli.id,
        contacto_id=None,
        divisa_original="CLP",
        tipo_cambio=1.0,
        notas=spec["notas"],
        estado=spec["estado"],
        historial_estados=[{"estado": spec["estado"], "fecha": datetime.now().isoformat()}],
    )
    db.add(cot)
    db.flush()

    items = []
    for (prod_idx, prov_idx, cantidad, costo, margen, personalizacion) in spec["items"]:
        dummy = ItemCotizacionCreate(
            producto_id=producto_rows[prod_idx].id,
            proveedor_id=proveedor_rows[prov_idx].id,
            descripcion=producto_rows[prod_idx].nombre,
            cantidad=cantidad,
            costo_original=costo,
            divisa_origen="USD",
            tipo_cambio=TC_USD_CLP,
            peso_kg=round(cantidad * 0.25, 2),
            volumen_m3=round(cantidad * 0.0012, 3),
            tipo_flete="Aereo",
            margen_pct=margen,
            descuento_pct=0,
            tipo_personalizacion=personalizacion,
            iva_pct=19,
        )
        calc = calcular_item(dummy)
        item = ItemCotizacion(
            cotizacion_id=cot.id,
            producto_id=dummy.producto_id,
            proveedor_id=dummy.proveedor_id,
            descripcion=dummy.descripcion,
            cantidad=dummy.cantidad,
            costo_original=dummy.costo_original,
            divisa_origen=dummy.divisa_origen,
            tipo_cambio=dummy.tipo_cambio,
            peso_kg=dummy.peso_kg,
            volumen_m3=dummy.volumen_m3,
            tipo_flete=dummy.tipo_flete,
            costo_flete=calc["costo_flete"],
            costo_envio=0,
            imagen_url="",
            margen_pct=dummy.margen_pct,
            descuento_pct=0,
            tipo_personalizacion=dummy.tipo_personalizacion,
            iva_pct=19,
            precio_venta_unitario=calc["precio_venta_unitario"],
            subtotal=calc["subtotal"],
            iva_monto=calc["iva_monto"],
            total=calc["total"],
        )
        db.add(item)
        items.append(item)

    db.flush()
    return (cot, items)


def _seed_importacion(db, cot, producto_rows, proveedor_rows) -> Importacion:
    items_data = [
        {"producto_id": producto_rows[0].id, "descripcion": producto_rows[0].nombre,
         "cantidad": 120, "precio_unitario_fabrica": 3.4, "divisa": "USD", "margen_pct": 35},
        {"producto_id": producto_rows[1].id, "descripcion": producto_rows[1].nombre,
         "cantidad": 60, "precio_unitario_fabrica": 5.8, "divisa": "USD", "margen_pct": 35},
    ]
    costos = [
        {"proveedor_id": proveedor_rows[4].id, "categoria": "Flete_Aereo_Int", "tipo_costo": "flete", "monto": 1850, "divisa": "USD", "notas": "Aereo Shanghai → Santiago"},
        {"proveedor_id": proveedor_rows[4].id, "categoria": "Seguro_Internacional", "tipo_costo": "seguro", "monto": 190, "divisa": "USD", "notas": ""},
        {"proveedor_id": proveedor_rows[4].id, "categoria": "Honorarios_Agente_Aduana", "tipo_costo": "honorarios", "monto": 320000, "divisa": "CLP", "notas": ""},
        {"proveedor_id": proveedor_rows[4].id, "categoria": "Flete_Terrestre_Local", "tipo_costo": "flete_local", "monto": 180000, "divisa": "CLP", "notas": ""},
    ]
    imp = Importacion(
        correlativo=f"IMP-{ANIO}-0001",
        estado="Borrador",
        transporte="Aereo",
        cert_origen=True,
        tc_usd_clp=TC_USD_CLP,
        tc_brl_usd=0.18,
        contingencia_pct=2,
        notas="Importación de vestuario corporativo generada para la demo.",
        cotizacion_id=cot.id,
        historial_estados=[{"estado": "Borrador", "fecha": datetime.now().isoformat()}],
    )
    db.add(imp)
    db.flush()

    resultado = calcular_importacion(
        items=items_data,
        costos=costos,
        tc_usd_clp=TC_USD_CLP,
        tc_brl_usd=0.18,
        contingencia_pct=2,
        cert_origen=True,
    )

    item_models = []
    for it, info in zip(items_data, resultado["items"]):
        item = ImportacionItem(
            importacion_id=imp.id,
            producto_id=it["producto_id"],
            descripcion=it["descripcion"],
            cantidad=it["cantidad"],
            precio_unitario_fabrica=it["precio_unitario_fabrica"],
            divisa=it["divisa"],
            margen_pct=it["margen_pct"],
            costo_fob_usd=info["fob_usd"],
            costo_cif_usd=info["cif_usd"],
            costo_unitario_neto_clp=info["costo_unitario_neto_clp"],
            precio_venta_neto_clp=info["precio_venta_neto_clp"],
            iva_venta_clp=info["iva_venta_clp"],
            precio_venta_total_clp=info["precio_venta_total_clp"],
        )
        db.add(item)
        item_models.append(item)

    for c in costos:
        db.add(ImportacionCosto(
            importacion_id=imp.id,
            proveedor_id=c["proveedor_id"],
            categoria=c["categoria"],
            tipo_costo=c["tipo_costo"],
            monto=c["monto"],
            divisa=c["divisa"],
            notas=c["notas"],
        ))

    db.add(ImportacionProveedor(
        importacion_id=imp.id,
        proveedor_id=proveedor_rows[0].id,
        categoria_id=proveedor_rows[0].categoria_id,
    ))
    db.add(ImportacionProveedor(
        importacion_id=imp.id,
        proveedor_id=proveedor_rows[4].id,
        categoria_id=proveedor_rows[4].categoria_id,
    ))

    cot.importacion_id = imp.id
    db.flush()
    return imp


def _seed_orden_compra(db, cot, items_cot, proveedor) -> OrdenCompra:
    oc = OrdenCompra(
        correlativo=f"OC-{ANIO}-0001",
        cotizacion_id=cot.id,
        proveedor_id=proveedor.id,
        estado="Pendiente",
        notas="Orden de compra de prueba para la demo.",
    )
    db.add(oc)
    db.flush()

    for item_cot in items_cot:
        subtotal = round(item_cot.costo_original * item_cot.cantidad, 2)
        db.add(ItemOrdenCompra(
            orden_id=oc.id,
            producto_id=item_cot.producto_id,
            descripcion=item_cot.descripcion,
            cantidad=item_cot.cantidad,
            costo_unitario=round(item_cot.costo_original, 2),
            divisa=item_cot.divisa_origen or "USD",
            tipo_personalizacion=item_cot.tipo_personalizacion,
            subtotal=subtotal,
        ))
    return oc