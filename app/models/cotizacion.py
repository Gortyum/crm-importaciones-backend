from datetime import datetime

from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Cotizacion(Base):
    __tablename__ = "cotizaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    correlativo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    cliente_id: Mapped[int] = mapped_column(Integer, ForeignKey("clientes.id"), nullable=False)
    contacto_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("contactos.id"), nullable=True)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="Creada")
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    divisa_original: Mapped[str] = mapped_column(String(5), nullable=False, default="CLP")
    tipo_cambio: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    notas: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    historial_estados: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=list)
    importacion_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("importaciones.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cliente = relationship("Cliente", back_populates="cotizaciones")
    contacto = relationship("Contacto")
    importacion = relationship(
        "Importacion",
        back_populates="cotizacion",
        foreign_keys="Importacion.cotizacion_id",
    )
    items = relationship("ItemCotizacion", back_populates="cotizacion", cascade="all, delete-orphan")


class ItemCotizacion(Base):
    __tablename__ = "items_cotizacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cotizacion_id: Mapped[int] = mapped_column(Integer, ForeignKey("cotizaciones.id"), nullable=False)
    producto_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("productos.id"), nullable=True)
    proveedor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("proveedores.id"), nullable=True)
    descripcion: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    costo_original: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    divisa_origen: Mapped[str] = mapped_column(String(5), nullable=False, default="CLP")
    tipo_cambio: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    peso_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    volumen_m3: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    tipo_flete: Mapped[str] = mapped_column(String(20), nullable=False, default="Terrestre")
    costo_flete: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    costo_envio: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    imagen_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    margen_pct: Mapped[float] = mapped_column(Float, nullable=False, default=30)
    descuento_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    tipo_personalizacion: Mapped[str] = mapped_column(String(30), nullable=False, default="Serigrafia")
    iva_pct: Mapped[float] = mapped_column(Float, nullable=False, default=19)
    precio_venta_unitario: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    iva_monto: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    cotizacion = relationship("Cotizacion", back_populates="items")
