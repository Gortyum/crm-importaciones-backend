import asyncio

import httpx


async def _get_json(client: httpx.AsyncClient, url: str) -> dict:
    resp = await client.get(url)
    return resp.json()


async def obtener_tipo_cambio() -> dict:
    fallback = {"USD": 950.0, "EUR": 1025.0, "BRL": 180.0}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            dolar, euro, forex = await asyncio.gather(
                _get_json(client, "https://mindicador.cl/api/dolar"),
                _get_json(client, "https://mindicador.cl/api/euro"),
                _get_json(client, "https://open.er-api.com/v6/latest/USD"),
            )
            usd_clp = dolar["serie"][0]["valor"]
            eur_clp = euro["serie"][0]["valor"]

            brl_per_usd = forex["rates"].get("BRL")
            if isinstance(brl_per_usd, (int, float)) and brl_per_usd > 0:
                # 1 BRL en CLP = CLP por USD / BRL por USD
                brl_clp = round(usd_clp / brl_per_usd, 2)
            else:
                # Estimación conservadora si falla la fuente de BRL: 1 EUR ~ 6.05 BRL
                brl_clp = round(eur_clp / 6.05, 2)

            return {"USD": round(usd_clp, 2), "EUR": round(eur_clp, 2), "BRL": brl_clp}
    except Exception:
        return fallback