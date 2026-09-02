from app.schemas.cotizacion import ItemCotizacionCreate


TARIFAS_FLETE_KG = {
    "Aereo": 4500,
    "Terrestre": 1800,
    "Maritimo": 900,
}

TARIFAS_FLETE_M3 = {
    "Aereo": 35000,
    "Terrestre": 12000,
    "Maritimo": 5000,
}


def calcular_costo_flete(item: ItemCotizacionCreate, tipo_cambio: float) -> float:
    if item.costo_flete > 0:
        return item.costo_flete * tipo_cambio

    tarifa_kg = TARIFAS_FLETE_KG.get(item.tipo_flete, 1800)
    tarifa_m3 = TARIFAS_FLETE_M3.get(item.tipo_flete, 12000)

    costo_por_peso = item.peso_kg * tarifa_kg
    costo_por_volumen = item.volumen_m3 * tarifa_m3

    return max(costo_por_peso, costo_por_volumen)


def calcular_item(item: ItemCotizacionCreate, tipo_cambio: float) -> dict:
    costo_clp = item.costo_original * tipo_cambio
    flete = calcular_costo_flete(item, tipo_cambio)
    envio = item.costo_envio

    subtotal_base = (costo_clp + flete + envio) * item.cantidad
    con_margen = subtotal_base * (1 + item.margen_pct / 100)
    con_descuento = con_margen * (1 - item.descuento_pct / 100)

    precio_venta_unitario = con_descuento / item.cantidad if item.cantidad > 0 else 0
    iva_monto = con_descuento * (item.iva_pct / 100)
    total = con_descuento + iva_monto

    return {
        "costo_flete": flete,
        "precio_venta_unitario": round(precio_venta_unitario, 0),
        "subtotal": round(con_descuento, 0),
        "iva_monto": round(iva_monto, 0),
        "total": round(total, 0),
    }
