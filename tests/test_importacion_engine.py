"""Tests de consistencia del motor de costeo de importaciones.

Verifica las conversiones de divisa, la construcción de FOB/CIF, aranceles,
contingencia e IVA de importación, y que los totales de venta resultantes del
costeo (landed) cuadren línea por línea y en el agregado.
"""
import pytest

from app.services.importacion_engine import calcular_importacion, to_clp, to_usd

ITEMS = [
    {"producto_id": 1, "descripcion": "Polera", "cantidad": 10, "precio_unitario_fabrica": 5.0, "divisa": "USD", "margen_pct": 30},
    {"producto_id": 2, "descripcion": "Polo", "cantidad": 5, "precio_unitario_fabrica": 8.0, "divisa": "USD", "margen_pct": 40},
]

COSTOS = [
    {"categoria": "Flete_Aereo_Int", "tipo_costo": "flete", "monto": 300.0, "divisa": "USD"},
    {"categoria": "Seguro_Internacional", "tipo_costo": "seguro", "monto": 50.0, "divisa": "USD"},
    {"categoria": "Flete_Terrestre_Local", "tipo_costo": "flete_local", "monto": 100000.0, "divisa": "CLP"},
    {"categoria": "Otros", "tipo_costo": "otros", "monto": 50000.0, "divisa": "CLP"},
]

TC_USD_CLP = 950.0
TC_BRL_USD = 0.18


@pytest.fixture
def resultado():
    return calcular_importacion(
        items=ITEMS,
        costos=COSTOS,
        tc_usd_clp=TC_USD_CLP,
        tc_brl_usd=TC_BRL_USD,
        contingencia_pct=2,
        cert_origen=True,
    )


def test_conversiones_divisas():
    assert to_usd(100000, "CLP", TC_USD_CLP, TC_BRL_USD) == pytest.approx(100000 / 950)
    assert to_usd(100, "BRL", TC_USD_CLP, TC_BRL_USD) == pytest.approx(100 * 0.18)
    assert to_usd(100, "USD", TC_USD_CLP, TC_BRL_USD) == 100
    assert to_clp(100000, "CLP", TC_USD_CLP, TC_BRL_USD) == 100000
    assert to_clp(100, "USD", TC_USD_CLP, TC_BRL_USD) == pytest.approx(100 * 950)
    assert to_clp(100, "BRL", TC_USD_CLP, TC_BRL_USD) == pytest.approx(100 * 0.18 * 950)


def test_fob_cif_y_agregados(resultado):
    r = resultado
    assert r["fob_total_usd"] == pytest.approx(90.0, abs=0.01)
    assert r["flete_usd"] == pytest.approx(300.0)
    assert r["seguro_usd"] == pytest.approx(50.0)
    assert r["cif_total_usd"] == pytest.approx(440.0, abs=0.01)
    assert r["arancel_usd"] == pytest.approx(0.0)  # cert_origen=True -> mercosur 0
    assert r["extranjero_no_cif_usd"] == pytest.approx(0.0)
    assert r["contingencia_usd"] == pytest.approx(8.8, abs=0.01)
    assert r["gastos_locales_clp"] == pytest.approx(100000.0)
    assert r["otros_clp"] == pytest.approx(50000.0)


def test_costo_almacen_e_iva_importacion(resultado):
    r = resultado
    assert r["costo_almacen_clp"] == pytest.approx(448.8 * 950 + 150000, abs=2)
    assert r["iva_importacion_clp"] == pytest.approx(440 * 0.19 * 950, abs=2)
    assert r["costo_unitario_promedio_clp"] == pytest.approx((448.8 * 950 + 150000) / 15, abs=2)
    assert r["cantidad_total"] == 15


def test_totales_venta_consistentes(resultado):
    r = resultado
    neto = sum(i["subtotal_venta_clp"] for i in r["items"])
    assert r["totales_venta"]["neto"] == neto
    assert r["totales_venta"]["iva"] == sum(i["iva_linea_clp"] for i in r["items"])
    assert r["totales_venta"]["total"] == sum(i["total_linea_clp"] for i in r["items"])
    assert r["totales_venta"]["total"] == r["totales_venta"]["neto"] + r["totales_venta"]["iva"]


def test_items_linea_consistentes(resultado):
    for item in resultado["items"]:
        assert item["total_linea_clp"] == item["subtotal_venta_clp"] + item["iva_linea_clp"]
        assert item["iva_linea_clp"] == round(item["subtotal_venta_clp"] * 0.19)
        assert item["costo_unitario_neto_clp"] > 0
        assert item["precio_venta_neto_clp"] > item["costo_unitario_neto_clp"]  # el margen debe elevar el precio


def test_arancel_general_sin_certificado():
    r = calcular_importacion(
        items=ITEMS,
        costos=COSTOS,
        tc_usd_clp=TC_USD_CLP,
        tc_brl_usd=TC_BRL_USD,
        contingencia_pct=2,
        cert_origen=False,
    )
    assert r["config"]["arancel_pct"] == 6
    assert r["arancel_usd"] == pytest.approx(440 * 0.06, abs=0.02)


def test_item_en_brl_se_convierte_a_usd():
    items = [{"producto_id": 3, "descripcion": "Bolsa", "cantidad": 10, "precio_unitario_fabrica": 50.0, "divisa": "BRL", "margen_pct": 30}]
    r = calcular_importacion(
        items=items,
        costos=[],
        tc_usd_clp=950,
        tc_brl_usd=0.18,
        contingencia_pct=0,
        cert_origen=True,
    )
    assert r["fob_total_usd"] == pytest.approx(50 * 0.18 * 10, abs=0.02)