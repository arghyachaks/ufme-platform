from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import Tenant
from app.services.workflow import Actor, resolve_actor

DbSession = Annotated[Session, Depends(get_db)]


def current_tenant(db: DbSession) -> Tenant:
    """Until auth lands (Stage 5) every request uses the configured default tenant."""
    tenant = db.scalar(select(Tenant).where(Tenant.slug == settings.default_tenant))
    if tenant is None:
        raise NotFoundError(
            f"Tenant '{settings.default_tenant}' has no data. Seed it with `python -m app.seed --force`.",
            code="tenant_not_found",
        )
    return tenant


CurrentTenant = Annotated[Tenant, Depends(current_tenant)]


def current_actor(
    db: DbSession, tenant: CurrentTenant, x_ufme_user: Annotated[str | None, Header()] = None
) -> Actor:
    """Demo identity: the X-Ufme-User header picks a seeded user (the UI's "acting as" switcher)."""
    return resolve_actor(db, tenant, x_ufme_user)


CurrentActor = Annotated[Actor, Depends(current_actor)]
