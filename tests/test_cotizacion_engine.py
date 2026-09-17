"""Tests de consistencia del motor de cálculo de items de cotización.

Cualquier cambio en `calcular_item` que altere la fórmula (margen, flete,
descuento, IVA) debe mantener estas invariantes: los valores devueltos son
redondeos coherentes entre sí y los totales por línea cuadran.
"""
from app.schemas.cotizacion import ItemCotizacionCreate
from app.services.cotizacion_engine import calcular_item, calcular_costo_flete


def base_item(**over) -> ItemCotizacionCreate:
    data = dict(
        producto_id=1,
        proveedor_id=1,
        descripcion="Polera de prueba",
        cantidad=10,
        costo_original=5.0,
        divisa_origen="USD",
        tipo_cambio=950.0,
        peso_kg=20.0,
        volumen_m3=0.05,
        tipo_flete="Aereo",
        costo_flete=0,
        costo_envio=0,
        margen_pct=35,
        descuento_pct=0,
        tipo_personalizacion="Bordado",
        iva_pct=19,
    )
    data.update(over)
    return ItemCotizacionCreate(**data)


def test_caso_referencia_aereo():
    r = calcular_item(base_item())
    # costo 5 USD * 950 = 4750 CLP/unit; flete = max(peso, volumen) = 20*4500
    # subtotal = (4750 + 0) * 10 + 90000 = 137500; / (1 - 0.35) * (1 - 0)
    assert r["costo_flete"] == 90000
    assert r["subtotal"] == 211538
    assert r["precio_venta_unitario"] == 21154
    assert r["iva_monto"] == 40192
    assert r["total"] == 251731


def test_invariantes_de_redondeo_en_varias_configuraciones():
    for tipo_flete in ("Aereo", "Terrestre", "Maritimo"):
        for margen in (0, 10, 35, 99):
            for iva in (0, 19):
                it = base_item(tipo_flete=tipo_flete, margen_pct=margen, iva_pct=iva, descuento_pct=5)
                r = calcular_item(it)
                # el IVA y el total se redondean sobre el precio antes de descuento, ±1 de holgura
                assert abs(r["total"] - (r["subtotal"] + r["iva_monto"])) <= 1
                assert abs(r["iva_monto"] - round(r["subtotal"] * iva / 100)) <= 1
                assert abs(r["precio_venta_unitario"] - round(r["subtotal"] / it.cantidad)) <= 1
                if iva == 0:
                    assert r["iva_monto"] == 0
                    assert r["total"] == r["subtotal"]


def test_flete_manual_no_se_convierte_por_tipo_de_cambio():
    it = base_item(costo_flete=50000, tipo_cambio=999)
    r = calcular_item(it)
    # El flete manual se interpreta en CLP, por lo que NO se multiplica por TC
    assert r["costo_flete"] == 50000
    manual = calcular_costo_flete(it, it.tipo_cambio)
    assert manual == 50000


def test_flete_automatico_es_el_mayor_entre_peso_y_volumen():
    r = calcular_item(base_item(peso_kg=1, volumen_m3=2.0))  # 1*4500 vs 2*35000
    assert r["costo_flete"] == 70000
    r = calcular_item(base_item(peso_kg=100, volumen_m3=0.001))  # 100*4500 vs 0.001*35000
    assert r["costo_flete"] == 450000


def test_divisa_clp_no_convierte():
    r = calcular_item(base_item(costo_original=1000, divisa_origen="CLP", tipo_cambio=1.0))
    # costo = 1000 * 1; flete por peso 20kg * 4500 = 90000
    assert r["subtotal"] > 0


def test_margen_mayor_igual_100_no_divide_por_cero():
    r = calcular_item(base_item(margen_pct=100))
    assert r["subtotal"] > 0


def test_cantidad_cero_no_da_error():
    r = calcular_item(base_item(cantidad=0))
    assert r["precio_venta_unitario"] == 0
    # el flete (lote) se suma una sola vez aunque la cantidad sea 0
    # subtotal = flete / (1 - margen) = 90000 / 0.65
    assert r["subtotal"] == round(90000 / 0.65)