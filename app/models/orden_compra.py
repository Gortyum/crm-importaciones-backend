from datetime import datetime

from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrdenCompra(Base):
    __tablename__ = "ordenes_compra"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    correlativo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    cotizacion_id: Mapped[int] = mapped_column(Integer, ForeignKey("cotizaciones.id"), nullable=False)
    proveedor_id: Mapped[int] = mapped_column(Integer, ForeignKey("proveedores.id"), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="Pendiente")
    notas: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cotizacion = relationship("Cotizacion")
    proveedor = relationship("Proveedor")
    items = relationship("ItemOrdenCompra", back_populates="orden", cascade="all, delete-orphan")


class ItemOrdenCompra(Base):
    __tablename__ = "items_orden_compra"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    orden_id: Mapped[int] = mapped_column(Integer, ForeignKey("ordenes_compra.id"), nullable=False)
    producto_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("productos.id"), nullable=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    costo_unitario: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    divisa: Mapped[str] = mapped_column(String(5), nullable=False, default="CLP")
    tipo_personalizacion: Mapped[str] = mapped_column(String(30), nullable=False, default="Serigrafia")
    subtotal: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    notas: Mapped[str] = mapped_column(String(300), nullable=False, default="")

    orden = relationship("OrdenCompra", back_populates="items")
