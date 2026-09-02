from fastapi import APIRouter
from app.services.divisa import obtener_tipo_cambio

router = APIRouter(prefix="/api/divisas", tags=["divisas"])


@router.get("/cambio")
async def tipo_cambio():
    rates = await obtener_tipo_cambio()
    return {"monedas": rates}
