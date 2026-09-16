import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Product(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "products"

    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(100), default="")


class ProductVariant(UUIDPKMixin, TimestampMixin, Base):
    """Preço e estoque vivem aqui, nunca na cabeça do modelo — é o que as tools de
    catálogo (`lookup_product`, `check_stock`) leem. Ver ARCHITECTURE.md."""

    __tablename__ = "product_variants"

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), index=True)
    sku: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    size: Mapped[str] = mapped_column(String(20), default="")
    color: Mapped[str] = mapped_column(String(50), default="")
    price: Mapped[Numeric] = mapped_column(Numeric(10, 2))
    stock_qty: Mapped[int] = mapped_column(Integer, default=0)
