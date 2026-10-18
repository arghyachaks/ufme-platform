import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPk


class Role(UUIDPk, Timestamps, Base):
    __tablename__ = "role"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)


class AppUser(UUIDPk, Timestamps, Base):
    __tablename__ = "app_user"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_app_user_tenant_email"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(320))
    display_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), default="Invited")  # Active | Invited | Disabled
    mfa_enabled: Mapped[bool] = mapped_column(default=False)
    external_subject: Mapped[str | None] = mapped_column(String(255), unique=True)  # OIDC "sub"
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    roles: Mapped[list["UserRole"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserRole(UUIDPk, Timestamps, Base):
    """Role assignment, optionally scoped to specific legal entities (empty list = all entities)."""

    __tablename__ = "user_role"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role_user_role"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("role.id", ondelete="CASCADE"), index=True)
    entity_codes: Mapped[list[str]] = mapped_column(JSON, default=list)

    user: Mapped[AppUser] = relationship(back_populates="roles")
    role: Mapped[Role] = relationship()
