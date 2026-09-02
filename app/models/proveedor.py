from datetime import datetime

from sqlalchemy import Integer, String, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProveedorCategoria(Base):
    __tablename__ = "proveedor_categorias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)

    proveedores = relationship("Proveedor", back_populates="categoria")


class Proveedor(Base):
    __tablename__ = "proveedores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    tax_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    pais_origen: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    etiquetas_productos: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=list)
    categoria_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("proveedor_categorias.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    categoria = relationship("ProveedorCategoria", back_populates="proveedores")