"""Configuración de pytest: bases aisladas (SQLite temporal) y sin red.

IMPORTANTE: se deben fijar las variables de entorno ANTES de importar la app,
porque `app.database` lee la URL de conexión al importar el módulo.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".testdata")
os.makedirs(_DATA, exist_ok=True)


def _sqlite(name: str) -> str:
    return "sqlite:///" + os.path.join(_DATA, name).replace("\\", "/")


os.environ["SQLITE_URL"] = _sqlite("test_app.db")
os.environ["DEMO_DATABASE_URL"] = _sqlite("test_demo.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.services import divisa  # noqa: E402


@pytest.fixture(autouse=True)
def _sin_red(monkeypatch):
    """Fija el tipo de cambio para no depender de APIs externas en los tests."""
    async def _tipo_cambio_fijo():
        return {"USD": 950.0, "EUR": 1025.0, "BRL": 180.0}

    monkeypatch.setattr(divisa, "obtener_tipo_cambio", _tipo_cambio_fijo)
    for nombre in ("app.routers.divisas", "app.services.referencias"):
        modulo = sys.modules.get(nombre)
        if modulo is not None and hasattr(modulo, "obtener_tipo_cambio"):
            monkeypatch.setattr(modulo, "obtener_tipo_cambio", _tipo_cambio_fijo)


@pytest.fixture(autouse=True)
def _tablas_limpias():
    """Recrea las tablas para partir siempre de una base vacía."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers():
    from app.services.auth_service import crear_token

    return {"Authorization": f"Bearer {crear_token('tester')}"}