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
    # El flete manual se interpreta en CLP (igual que costo_envio),
    # por lo que NO se multiplica por el tipo de cambio.
    if item.costo_flete > 0:
        return item.costo_flete

    tarifa_kg = TARIFAS_FLETE_KG.get(item.tipo_flete, 1800)
    tarifa_m3 = TARIFAS_FLETE_M3.get(item.tipo_flete, 12000)

    costo_por_peso = item.peso_kg * tarifa_kg
    costo_por_volumen = item.volumen_m3 * tarifa_m3

    return max(costo_por_peso, costo_por_volumen)


def calcular_item(item: ItemCotizacionCreate) -> dict:
    # El tipo de cambio vive en el item y corresponde a su divisa_origen:
    # cuantos CLP vale 1 unidad. Para divisa CLP vale 1 (sin conversion).
    costo_clp = item.costo_original * item.tipo_cambio
    flete = calcular_costo_flete(item, item.tipo_cambio)
    envio = item.costo_envio

    # El flete es el costo TOTAL de transporte del lote de ese item (no por unidad),
    # por lo que se suma una sola vez, fuera de la multiplicacion por cantidad.
    subtotal_base = (costo_clp + envio) * item.cantidad + flete
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
