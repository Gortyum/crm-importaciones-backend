from datetime import datetime

from sqlalchemy import Integer, String, ForeignKey, DateTime, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Documento(Base):
    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    correlativo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    cotizacion_id: Mapped[int] = mapped_column(Integer, ForeignKey("cotizaciones.id"), nullable=False)
    especificaciones: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cotizacion = relationship("Cotizacion")