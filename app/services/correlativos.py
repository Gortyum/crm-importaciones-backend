"""Correlativos: única fuente de la secuencia (prefijo + formato + conteo).

Una ``Serie`` describe el formato de una familia de correlativos y el número
siguiente se deriva del último registro con ese prefijo (por año cuando la
serie es anual). ``con_correlativo`` hace el insert seguro ante carreras:
reintenta con el siguiente número si dos peticiones piden el mismo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

TRAILING_NUMERO = re.compile(r"(\d+)\s*$")
MAX_INTENTOS = 5


class CorrelativoAgotadoError(Exception):
    """No se pudo asignar un correlativo único tras varios intentos."""


@dataclass(frozen=True)
class Serie:
    prefijo: str
    con_anio: bool = True
    ancho: int = 4
    separador: str = "-"

    def patron(self, anio: int | None = None) -> str:
        if self.con_anio:
            anio = anio or datetime.now().year
            return f"{self.prefijo}{self.separador}{anio}{self.separador}%"
        return f"{self.prefijo}%"

    def formatear(self, numero: int, anio: int | None = None) -> str:
        if self.con_anio:
            anio = anio or datetime.now().year
            numero = f"{anio}{self.separador}{numero:0{self.ancho}d}"
        return f"{self.prefijo}{self.separador}{numero}"


SERIE_DOCUMENTO = Serie(prefijo="PDF", con_anio=False, ancho=1, separador=" ")
SERIE_IMPORTACION = Serie(prefijo="IMP", con_anio=True, ancho=4, separador="-")
SERIE_ORDEN_COMPRA = Serie(prefijo="OC", con_anio=True, ancho=4, separador="-")
SERIE_COTIZACION = Serie(prefijo="COT", con_anio=True, ancho=4, separador="-")


def siguiente_correlativo(db: Session, modelo: type, serie: Serie) -> str:
    """Calcula el siguiente correlativo de la serie sin insertar nada."""
    ultimo = (
        db.query(modelo)
        .filter(modelo.correlativo.like(serie.patron()))
        .order_by(modelo.id.desc())
        .first()
    )
    numero = 1
    if ultimo and getattr(ultimo, "correlativo", None):
        match = TRAILING_NUMERO.search(ultimo.correlativo)
        if match:
            numero = int(match.group(1)) + 1
    return serie.formatear(numero)


def con_correlativo(
    db: Session,
    modelo: type,
    serie: Serie,
    construir,
):
    """Insertar una fila con correlativo único, reintentando ante colisión.

    ``construir(correlativo)`` debe agregar la/s fila/s a la sesión (add, flush,
    hijos) y devolver la fila principal; aquí se hace el commit y, si el
    correlativo colisiona (unique), se hace rollback y se repite con el
    siguiente número.
    """
    fila = None
    for _ in range(MAX_INTENTOS):
        correlativo = siguiente_correlativo(db, modelo, serie)
        try:
            fila = construir(correlativo)
            db.commit()
            db.refresh(fila)
            return fila
        except IntegrityError:
            db.rollback()
    raise CorrelativoAgotadoError(
        f"No se pudo asignar un correlativo único para la serie '{serie.prefijo}'"
    )