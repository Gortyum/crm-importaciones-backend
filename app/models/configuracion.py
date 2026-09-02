from sqlalchemy import Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConfigGlobal(Base):
    __tablename__ = "config_global"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    clave: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    valor: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    etiqueta: Mapped[str] = mapped_column(String(200), nullable=False, default="")