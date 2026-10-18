import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPk


class Tenant(UUIDPk, Timestamps, Base):
    __tablename__ = "tenant"

    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    region: Mapped[str] = mapped_column(String(32), default="eu-west")
    is_active: Mapped[bool] = mapped_column(default=True)

    entities: Mapped[list["LegalEntity"]] = relationship(back_populates="tenant")


class LegalEntity(UUIDPk, Timestamps, Base):
    __tablename__ = "legal_entity"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_legal_entity_tenant_code"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(64))
    currency: Mapped[str] = mapped_column(String(3))
    is_active: Mapped[bool] = mapped_column(default=True)

    tenant: Mapped[Tenant] = relationship(back_populates="entities")
