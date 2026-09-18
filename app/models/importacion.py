from datetime import datetime

from sqlalchemy import Integer, String, Float, DateTime, Boolean, ForeignKey, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Importacion(Base):
    __tablename__ = "importaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    correlativo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="Borrador")
    transporte: Mapped[str] = mapped_column(String(20), nullable=False, default="Aereo")
    cert_origen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tc_usd_clp: Mapped[float] = mapped_column(Float, nullable=False, default=920.0)
    tc_brl_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.18)
    contingencia_pct: Mapped[float] = mapped_column(Float, nullable=False, default=2)
    notas: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    cotizacion_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("cotizaciones.id"), nullable=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    historial_estados: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cotizacion = relationship(
        "Cotizacion",
        back_populates="importacion",
        foreign_keys=[cotizacion_id],
    )
    items = relationship("ImportacionItem", back_populates="importacion", cascade="all, delete-orphan")
    costos = relationship("ImportacionCosto", back_populates="importacion", cascade="all, delete-orphan")
    proveedores = relationship("ImportacionProveedor", back_populates="importacion", cascade="all, delete-orphan")


class ImportacionItem(Base):
    __tablename__ = "importacion_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    importacion_id: Mapped[int] = mapped_column(Integer, ForeignKey("importaciones.id"), nullable=False)
    producto_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("productos.id"), nullable=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    precio_unitario_fabrica: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    divisa: Mapped[str] = mapped_column(String(5), nullable=False, default="USD")
    margen_pct: Mapped[float] = mapped_column(Float, nullable=False, default=35)

    costo_fob_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    costo_cif_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    costo_unitario_neto_clp: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    precio_venta_neto_clp: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    iva_venta_clp: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    precio_venta_total_clp: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    importacion = relationship("Importacion", back_populates="items")


class ImportacionCosto(Base):
    __tablename__ = "importacion_costos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    importacion_id: Mapped[int] = mapped_column(Integer, ForeignKey("importaciones.id"), nullable=False)
    proveedor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("proveedores.id"), nullable=True)
    categoria: Mapped[str] = mapped_column(String(80), nullable=False)
    tipo_costo: Mapped[str] = mapped_column(String(30), nullable=False, default="otro")
    monto: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    divisa: Mapped[str] = mapped_column(String(5), nullable=False, default="USD")
    notas: Mapped[str] = mapped_column(String(300), nullable=False, default="")

    importacion = relationship("Importacion", back_populates="costos")
    proveedor = relationship("Proveedor")


class ImportacionProveedor(Base):
    __tablename__ = "importacion_proveedores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    importacion_id: Mapped[int] = mapped_column(Integer, ForeignKey("importaciones.id"), nullable=False)
    proveedor_id: Mapped[int] = mapped_column(Integer, ForeignKey("proveedores.id"), nullable=False)
    categoria_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("proveedor_categorias.id"), nullable=True)

    importacion = relationship("Importacion", back_populates="proveedores")
    proveedor = relationship("Proveedor")
    categoria = relationship("ProveedorCategoria")