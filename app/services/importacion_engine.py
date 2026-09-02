COSTOS_POR_TRANSPORTE = {
    "Courier": [
        {"categoria": "Flete_Courier", "tipo": "flete"},
        {"categoria": "Gastos_Despacho_Courier", "tipo": "despacho"},
        {"categoria": "Flete_Terrestre_Local", "tipo": "flete_local"},
    ],
    "Aereo": [
        {"categoria": "Flete_Aereo_Int", "tipo": "flete"},
        {"categoria": "Seguro_Internacional", "tipo": "seguro"},
        {"categoria": "Gastos_Terminal_Aereo", "tipo": "despacho"},
        {"categoria": "Honorarios_Agente_Aduana", "tipo": "honorarios"},
        {"categoria": "Flete_Terrestre_Local", "tipo": "flete_local"},
    ],
    "Terrestre": [
        {"categoria": "Flete_Terrestre_Int", "tipo": "flete"},
        {"categoria": "Seguro_Transito_Terr", "tipo": "seguro"},
        {"categoria": "Gastos_Frontera_PuertoSeco", "tipo": "despacho"},
        {"categoria": "Honorarios_Agente_Aduana", "tipo": "honorarios"},
        {"categoria": "Flete_Terrestre_Local", "tipo": "flete_local"},
    ],
}

CATEGORIAS_COSTO = {
    "Flete_Courier": "Flete Courier (Brasil → Chile)",
    "Gastos_Despacho_Courier": "Gastos Despacho Courier",
    "Flete_Aereo_Int": "Flete Aéreo Internacional",
    "Seguro_Internacional": "Seguro Internacional",
    "Gastos_Terminal_Aereo": "Gastos Terminal Aérea",
    "Flete_Terrestre_Int": "Flete Terrestre Internacional",
    "Seguro_Transito_Terr": "Seguro de Tránsito Terrestre",
    "Gastos_Frontera_PuertoSeco": "Gastos Frontera / Puerto Seco",
    "Honorarios_Agente_Aduana": "Honorarios Agente de Aduana",
    "Flete_Terrestre_Local": "Flete Terrestre Local (Chile)",
}


def to_usd(monto: float, divisa: str, tc_usd_clp: float, tc_brl_usd: float) -> float:
    d = (divisa or "USD").upper()
    if d == "CLP":
        return monto / tc_usd_clp if tc_usd_clp else 0
    if d == "BRL":
        return monto * tc_brl_usd
    return monto


def calcular_importacion(
    items: list,
    costos: list,
    tc_usd_clp: float,
    tc_brl_usd: float,
    contingencia_pct: float,
    cert_origen: bool,
    arancel_general: float = 6,
    arancel_mercosur: float = 0,
    iva_pct: float = 19,
) -> dict:
    arancel_pct = arancel_mercosur if cert_origen else arancel_general

    items_info = []
    fob_total = 0.0
    for it in items:
        precio_usd = to_usd(it["precio_unitario_fabrica"], it["divisa"], tc_usd_clp, tc_brl_usd)
        fob_item = precio_usd * it["cantidad"]
        fob_total += fob_item
        items_info.append({**it, "precio_usd": precio_usd, "fob_usd": fob_item})

    flete_usd = 0.0
    seguro_usd = 0.0
    extranjero_no_cif_usd = 0.0
    gastos_locales_clp = 0.0
    for c in costos:
        tipo = c["tipo_costo"]
        monto_usd = to_usd(c["monto"], c["divisa"], tc_usd_clp, tc_brl_usd)
        if c["divisa"] and c["divisa"].upper() == "CLP":
            gastos_locales_clp += c["monto"]
        elif tipo == "flete":
            flete_usd += monto_usd
        elif tipo == "seguro":
            seguro_usd += monto_usd
        else:
            extranjero_no_cif_usd += monto_usd

    cif_total_usd = fob_total + flete_usd + seguro_usd
    arancel_usd = cif_total_usd * (arancel_pct / 100)

    base_contingencia_usd = cif_total_usd + extranjero_no_cif_usd
    contingencia_usd = base_contingencia_usd * (contingencia_pct / 100)
    sub_ext_seguro_usd = base_contingencia_usd + contingencia_usd

    costo_almacen_clp = (
        sub_ext_seguro_usd * tc_usd_clp
        + arancel_usd * tc_usd_clp
        + gastos_locales_clp
    )
    iva_importacion_clp = (cif_total_usd + arancel_usd) * (iva_pct / 100) * tc_usd_clp

    cantidad_total = sum(i["cantidad"] for i in items)
    unitario_promedio = costo_almacen_clp / cantidad_total if cantidad_total else 0

    items_out = []
    for it in items_info:
        cantidad = it["cantidad"] or 0
        share = it["fob_usd"] / fob_total if fob_total else (cantidad / cantidad_total if cantidad_total else 0)
        cif_item = it["fob_usd"] + (flete_usd + seguro_usd) * share
        landed_item = costo_almacen_clp * share
        unitario_item = landed_item / cantidad if cantidad else 0
        margen = it["margen_pct"]
        neto_unit = unitario_item / (1 - margen / 100) if margen < 100 else 0
        iva_unit = neto_unit * (iva_pct / 100)
        total_unit = neto_unit + iva_unit

        items_out.append({
            "producto_id": it["producto_id"],
            "descripcion": it["descripcion"],
            "cantidad": cantidad,
            "precio_unitario_fabrica": it["precio_unitario_fabrica"],
            "divisa": it["divisa"],
            "margen_pct": margen,
            "fob_usd": round(it["fob_usd"], 2),
            "cif_usd": round(cif_item, 2),
            "costo_unitario_neto_clp": round(unitario_item, 2),
            "precio_venta_neto_clp": round(neto_unit),
            "iva_venta_clp": round(iva_unit),
            "precio_venta_total_clp": round(total_unit),
        })

    return {
        "config": {
            "tc_usd_clp": tc_usd_clp,
            "tc_brl_usd": tc_brl_usd,
            "contingencia_pct": contingencia_pct,
            "cert_origen": cert_origen,
            "arancel_pct": arancel_pct,
            "iva_pct": iva_pct,
        },
        "fob_total_usd": round(fob_total, 2),
        "flete_usd": round(flete_usd, 2),
        "seguro_usd": round(seguro_usd, 2),
        "cif_total_usd": round(cif_total_usd, 2),
        "arancel_usd": round(arancel_usd, 2),
        "extranjero_no_cif_usd": round(extranjero_no_cif_usd, 2),
        "contingencia_usd": round(contingencia_usd, 2),
        "sub_total_extranjero_usd": round(sub_ext_seguro_usd, 2),
        "gastos_locales_clp": round(gastos_locales_clp, 2),
        "costo_almacen_clp": round(costo_almacen_clp),
        "iva_importacion_clp": round(iva_importacion_clp),
        "costo_unitario_promedio_clp": round(unitario_promedio),
        "cantidad_total": cantidad_total,
        "items": items_out,
        "totales_venta": {
            "neto": round(sum(i["precio_venta_neto_clp"] for i in items_out)),
            "iva": round(sum(i["iva_venta_clp"] for i in items_out)),
            "total": round(sum(i["precio_venta_total_clp"] for i in items_out)),
        },
    }