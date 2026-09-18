"""Tests de integración de cotizaciones vía API.

El objetivo es que el cálculo quede consistente entre todos los puntos de
salida: crear, listar, detalle, edición y pdf-data, y que las transiciones de
estado respeten las reglas relajadas (avanzar + cancelar, nunca retroceder).
"""
from datetime import datetime

from app.schemas.cotizacion import ItemCotizacionCreate
from app.services.cotizacion_engine import calcular_item


def crear_cliente(client, headers, nombre="Cliente Test", rut="76.111.222-3"):
    r = client.post("/api/clientes/", headers=headers, json={"razon_social": nombre, "rut": rut})
    assert r.status_code in (200, 201), r.text
    return r.json()


def crear_producto(client, headers, nombre="Polera Test"):
    r = client.post("/api/productos/", headers=headers, json={"nombre": nombre, "descripcion": nombre, "unidad": "Unidad"})
    assert r.status_code in (200, 201), r.text
    return r.json()


def item_payload(producto_id, cantidad=10, costo=5.0, divisa="USD", tc=950.0, margen=35):
    return {
        "producto_id": producto_id,
        "descripcion": "Polera de prueba",
        "cantidad": cantidad,
        "costo_original": costo,
        "divisa_origen": divisa,
        "tipo_cambio": tc,
        "peso_kg": round(cantidad * 0.25, 2),
        "volumen_m3": round(cantidad * 0.0012, 3),
        "tipo_flete": "Aereo",
        "costo_flete": 0,
        "costo_envio": 0,
        "margen_pct": margen,
        "descuento_pct": 0,
        "tipo_personalizacion": "Bordado",
        "iva_pct": 19,
    }


def crear_cotizacion(client, headers, cliente_id, items):
    r = client.post("/api/cotizaciones/", headers=headers, json={"cliente_id": cliente_id, "items": items})
    assert r.status_code == 201, r.text
    return r.json()


def test_crear_persiste_calculo_consistente(client, auth_headers):
    cli = crear_cliente(client, auth_headers)
    p1 = crear_producto(client, auth_headers, "Producto 1")
    p2 = crear_producto(client, auth_headers, "Producto 2")

    payloads = [
        item_payload(p1["id"], cantidad=10, costo=5.0),
        item_payload(p2["id"], cantidad=5, costo=8.0, margen=40),
    ]
    esperado = {p["producto_id"]: calcular_item(ItemCotizacionCreate(**p)) for p in payloads}

    cot = crear_cotizacion(client, auth_headers, cli["id"], payloads)

    assert cot["estado"] == "Creada"
    assert cot["historial_estados"][0]["estado"] == "Creada"
    assert cot["cliente"]["razon_social"] == "Cliente Test"

    for item in cot["items"]:
        exp = esperado[item["producto_id"]]
        assert item["subtotal"] == exp["subtotal"]
        assert item["iva_monto"] == exp["iva_monto"]
        assert item["total"] == exp["total"]
        assert item["precio_venta_unitario"] == exp["precio_venta_unitario"]
        assert item["total"] == item["subtotal"] + item["iva_monto"]
        assert item["iva_monto"] == round(item["subtotal"] * 0.19)

    total_items = sum(i["total"] for i in cot["items"])
    assert cot["total_general"] == total_items

    # listar y detalle devuelven el mismo total
    lista = client.get("/api/cotizaciones/", headers=auth_headers).json()
    assert lista[0]["total_general"] == total_items
    detalle = client.get(f"/api/cotizaciones/{cot['id']}", headers=auth_headers).json()
    assert detalle["total_general"] == total_items

    # pdf-data reporta los mismos agregados
    pdf = client.get(f"/api/cotizaciones/{cot['id']}/pdf-data", headers=auth_headers).json()
    assert pdf["subtotal_general"] == sum(i["subtotal"] for i in cot["items"])
    assert pdf["iva_general"] == sum(i["iva_monto"] for i in cot["items"])
    assert pdf["total_general"] == total_items


def test_actualizar_recalcula_totales(client, auth_headers):
    cli = crear_cliente(client, auth_headers)
    p1 = crear_producto(client, auth_headers)
    cot = crear_cotizacion(client, auth_headers, cli["id"], [item_payload(p1["id"], cantidad=10)])

    payload_editado = item_payload(p1["id"], cantidad=20, costo=6.0)
    exp = calcular_item(ItemCotizacionCreate(**payload_editado))
    r = client.put(
        f"/api/cotizaciones/{cot['id']}",
        headers=auth_headers,
        json={"cliente_id": cli["id"], "items": [payload_editado]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["items"][0]["cantidad"] == 20
    assert body["items"][0]["total"] == exp["total"]
    assert body["total_general"] == sum(i["total"] for i in body["items"])


def test_pdf_emitido_bloquea_edicion(client, auth_headers):
    cli = crear_cliente(client, auth_headers)
    p1 = crear_producto(client, auth_headers)
    cot = crear_cotizacion(client, auth_headers, cli["id"], [item_payload(p1["id"])])

    r = client.get(f"/api/cotizaciones/{cot['id']}/pdf-data", headers=auth_headers)
    assert r.status_code == 200

    r = client.put(
        f"/api/cotizaciones/{cot['id']}",
        headers=auth_headers,
        json={"cliente_id": cli["id"], "items": [item_payload(p1["id"], cantidad=99)]},
    )
    assert r.status_code == 409


def test_transiciones_relajadas_y_terminales(client, auth_headers):
    cli = crear_cliente(client, auth_headers)
    p1 = crear_producto(client, auth_headers)

    # avanzar saltando etapas debe funcionar
    cot = crear_cotizacion(client, auth_headers, cli["id"], [item_payload(p1["id"])])
    r = client.patch(f"/api/cotizaciones/{cot['id']}/estado", headers=auth_headers, json={"estado": "En Produccion"})
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "En Produccion"
    assert len(r.json()["historial_estados"]) == 2

    # retroceder debe rechazarse
    r = client.patch(f"/api/cotizaciones/{cot['id']}/estado", headers=auth_headers, json={"estado": "Creada"})
    assert r.status_code == 400

    # cancelar desde un estado activo debe permitirse
    cot2 = crear_cotizacion(client, auth_headers, cli["id"], [item_payload(p1["id"])])
    r = client.patch(f"/api/cotizaciones/{cot2['id']}/estado", headers=auth_headers, json={"estado": "Cancelada"})
    assert r.status_code == 200
    assert r.json()["estado"] == "Cancelada"

    # Entregada es terminal: no admite salida
    cot3 = crear_cotizacion(client, auth_headers, cli["id"], [item_payload(p1["id"])])
    r = client.patch(f"/api/cotizaciones/{cot3['id']}/estado", headers=auth_headers, json={"estado": "Entregada"})
    assert r.status_code == 200
    r = client.patch(f"/api/cotizaciones/{cot3['id']}/estado", headers=auth_headers, json={"estado": "Cancelada"})
    assert r.status_code == 400


def test_correlativos_secuenciales(client, auth_headers):
    cli = crear_cliente(client, auth_headers)
    p1 = crear_producto(client, auth_headers)

    now = datetime.now()
    prefijo = f"COT-{now.year}-{now.month:02d}"
    c1 = crear_cotizacion(client, auth_headers, cli["id"], [item_payload(p1["id"])])
    c2 = crear_cotizacion(client, auth_headers, cli["id"], [item_payload(p1["id"])])
    assert c1["correlativo"] == f"{prefijo}-0001"
    assert c2["correlativo"] == f"{prefijo}-0002"


def test_importacion_vinculada_recalcula_landed(client, auth_headers):
    cli = crear_cliente(client, auth_headers)
    p1 = crear_producto(client, auth_headers)
    p2 = crear_producto(client, auth_headers)

    cot = crear_cotizacion(
        client,
        auth_headers,
        cli["id"],
        [item_payload(p1["id"], cantidad=10, costo=5.0, margen=30), item_payload(p2["id"], cantidad=5, costo=8.0, margen=40)],
    )

    r = client.post(f"/api/cotizaciones/{cot['id']}/crear-importacion", headers=auth_headers)
    assert r.status_code == 200, r.text

    detalle = client.get(f"/api/cotizaciones/{cot['id']}", headers=auth_headers).json()
    assert detalle["importacion_id"] is not None
    assert detalle["importacion_correlativo"].startswith("IMP-")
    assert detalle["total_general"] == sum(i["total"] for i in detalle["items"])

    for item in detalle["items"]:
        assert item["total"] == item["subtotal"] + item["iva_monto"]
        assert item["iva_monto"] == round(item["subtotal"] * 0.19)
        assert item["precio_venta_unitario"] > 0

    pdf = client.get(f"/api/cotizaciones/{cot['id']}/pdf-data", headers=auth_headers).json()
    assert pdf["total_general"] == detalle["total_general"]


def test_descripcion_larga_se_conserva_entera(client, auth_headers):
    """Las descripciones de producto largas no deben truncarse (varchar 300)."""
    descripcion_larga = (
        "Neceser de mano personalizado en neopreno. Material: neopreno de 3 mm, "
        "resistente, flexible y con protección ante impactos leves. Revestimiento: "
        "doble capa de poliéster. Medidas: 20 × 15 × 26 cm (alto × ancho). Asa: "
        "cinta CTF reforzada para transporte manual. Personalización: apto para "
        "logotipos, diseños y estampados a todo color en alta definición."
    ) * 3
    assert len(descripcion_larga) > 300

    cli = crear_cliente(client, auth_headers)
    p1 = crear_producto(client, auth_headers, "Neceser Neopreno")
    payload = item_payload(p1["id"], cantidad=60, costo=15.75, divisa="BRL", tc=190.97, margen=20)
    payload["descripcion"] = descripcion_larga

    cot = crear_cotizacion(client, auth_headers, cli["id"], [payload])
    assert cot["items"][0]["descripcion"] == descripcion_larga

    detalle = client.get(f"/api/cotizaciones/{cot['id']}", headers=auth_headers).json()
    assert detalle["items"][0]["descripcion"] == descripcion_larga