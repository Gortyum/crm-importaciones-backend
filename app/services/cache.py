"""Caché de datos de referencia con respaldo en memoria.

Usa Redis cuando `REDIS_URL` está definida (producción/Railway).
Si no está configurada o Redis no responde, cae a un cache simple en memoria.
TP de esto: los datos de referencia (monedas, config, estados, catálogos)
se cargan al iniciar sesión y no se recalculan en cada login.
"""

import json
import os
import threading
import time
from typing import Any

REDIS_URL = os.getenv("REDIS_URL", "")
_TTL_DEFAULT = int(os.getenv("REFERENCIAS_TTL_SEG", "900"))

_mem: dict[str, dict[str, Any]] = {}
_mem_lock = threading.Lock()

_redis_client: Any = None


def _cliente_redis():
    """Devuelve el cliente Redis si está disponible, o None."""
    global _redis_client
    if not REDIS_URL:
        return None
    if _redis_client is None:
        try:
            import redis

            cliente = redis.Redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            cliente.ping()
            _redis_client = cliente
        except Exception:
            _redis_client = None
    return _redis_client


def backend_activo() -> str:
    """Indica el backend de caché en uso: 'redis' o 'memoria'."""
    return "redis" if _cliente_redis() is not None else "memoria"


def cache_get(key: str) -> Any:
    r = _cliente_redis()
    if r is not None:
        try:
            raw = r.get(key)
            return json.loads(raw) if raw is not None else None
        except Exception:
            return None
    with _mem_lock:
        item = _mem.get(key)
        if not item:
            return None
        if item["exp"] < time.time():
            _mem.pop(key, None)
            return None
        return item["val"]


def cache_set(key: str, value: Any, ttl: int = _TTL_DEFAULT) -> None:
    r = _cliente_redis()
    if r is not None:
        try:
            r.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))
            return
        except Exception:
            pass
    with _mem_lock:
        _mem[key] = {"val": value, "exp": time.time() + ttl}


def cache_clear(prefix: str) -> None:
    """Elimina todas las claves que empiecen con el prefijo dado."""
    r = _cliente_redis()
    if r is not None:
        try:
            for k in r.scan_iter(match=f"{prefix}*"):
                r.delete(k)
            return
        except Exception:
            pass
    with _mem_lock:
        for k in list(_mem):
            if k.startswith(prefix):
                _mem.pop(k, None)