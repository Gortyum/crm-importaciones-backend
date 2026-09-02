from datetime import datetime

from sqlalchemy import Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    rut: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    direccion: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    giro: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    contactos = relationship("Contacto", back_populates="cliente", cascade="all, delete-orphan")
    cotizaciones = relationship("Cotizacion", back_populates="cliente")


class Contacto(Base):
    __tablename__ = "contactos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cliente_id: Mapped[int] = mapped_column(Integer, ForeignKey("clientes.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    cargo: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    telefono: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    es_principal: Mapped[bool] = mapped_column(default=False)

    cliente = relationship("Cliente", back_populates="contactos")
