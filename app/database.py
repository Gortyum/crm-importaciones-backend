import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./crm_erp.db")


def _resolve_sqlite_url(url: str) -> str:
    if not url.startswith("sqlite:///"):
        return url
    path = url.replace("sqlite:///", "", 1)
    if path.startswith("/") or ":" in path[:2] or path == ":memory:":
        return url
    return f"sqlite:///{(PROJECT_ROOT / path).resolve().as_posix()}"


_resolved_url = _resolve_sqlite_url(DATABASE_URL)

connect_args = {"check_same_thread": False} if _resolved_url.startswith("sqlite") else {}
engine = create_engine(_resolved_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
