import httpx


async def obtener_tipo_cambio() -> dict:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("https://mindicador.cl/api/dolar")
            data = resp.json()
            usd_clp = data["serie"][0]["valor"]

            resp2 = await client.get("https://mindicador.cl/api/euro")
            data2 = resp2.json()
            eur_clp = data2["serie"][0]["valor"]

            return {"USD": usd_clp, "EUR": eur_clp, "BRL": round(eur_clp * 1.08, 2)}
    except Exception:
        return {"USD": 950, "EUR": 1025, "BRL": 1107}
