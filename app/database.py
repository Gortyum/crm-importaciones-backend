import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _build_database_url() -> str:
    """Devuelve la URL de conexión, priorizando PostgreSQL.

    Railway inyecta el plugin Postgres como variables de entorno:
      - DATABASE_URL (p. ej. ${{Postgres.DATABASE_URL}} -> postgres://user:pwd@host:port/db)
      - PGHOST / PGPORT / PGDATABASE / PGUSER / PGPASSWORD
    También acepta POSTGRES_URL / POSTGRESQL_URL por compatibilidad.
    Si ninguna está configurada, cae a SQLite local (desarrollo).
    """
    for var in ("DATABASE_URL", "POSTGRES_URL", "POSTGRESQL_URL"):
        url = os.getenv(var)
        if url:
            # Railway entrega "postgres://"; SQLAlchemy requiere "postgresql+psycopg2://"
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg2://", 1)
            return url

    host = os.getenv("PGHOST") or os.getenv("POSTGRES_HOST")
    if host:
        user = os.getenv("PGUSER") or os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD", "")
        db = os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB", "postgres")
        port = os.getenv("PGPORT") or os.getenv("POSTGRES_PORT", "5432")
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

    return os.getenv("SQLITE_URL", "sqlite:///./crm_erp.db")


DATABASE_URL = _build_database_url()


def _resolve_sqlite_url(url: str) -> str:
    # Solo se aplica al fallback SQLite local; Postgres se usa tal cual.
    if not url.startswith("sqlite:///"):
        return url
    path = url.replace("sqlite:///", "", 1)
    if path.startswith("/") or ":" in path[:2] or path == ":memory:":
        return url
    return f"sqlite:///{(PROJECT_ROOT / path).resolve().as_posix()}"


_resolved_url = _resolve_sqlite_url(DATABASE_URL)

if _resolved_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {}

engine = create_engine(_resolved_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
