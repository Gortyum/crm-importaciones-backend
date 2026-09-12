from datetime import datetime

from sqlalchemy import Integer, String, Text, DateTime, Boolean, BigInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Archivo(Base):
    """Metadatos de un archivo almacenado en Cloudflare R2.

    Solo guarda la referencia (object_key) y metadatos; nunca el contenido.
    """

    __tablename__ = "archivos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre_original: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    carpeta: Mapped[str] = mapped_column(String(50), nullable=False)
    entidad_tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    entidad_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tamano: Mapped[int] = mapped_column(BigInteger, nullable=False)
    es_publico: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    @property
    def key(self) -> str:
        """Ruta completa dentro del bucket: <carpeta>/<uuid>.<ext>"""
        return self.object_key