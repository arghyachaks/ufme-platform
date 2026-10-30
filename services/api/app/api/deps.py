"""Request dependencies: authenticated principal -> tenant (pinned in the database) -> acting user."""

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ForbiddenError, NotFoundError
from app.core.security import Principal, authenticate
from app.db.session import get_db
from app.db.tenancy import pin_tenant
from app.models import Tenant
from app.services.workflow import Actor, resolve_actor

DbSession = Annotated[Session, Depends(get_db)]


def current_principal(
    authorization: Annotated[str | None, Header()] = None,
    x_ufme_user: Annotated[str | None, Header()] = None,
) -> Principal:
    """Who is calling: a verified OIDC token, or (dev mode only) the X-Ufme-User header."""
    return authenticate(authorization, x_ufme_user)


CurrentPrincipal = Annotated[Principal, Depends(current_principal)]


def current_tenant(db: DbSession, principal: CurrentPrincipal) -> Tenant:
    """The caller's tenant, from their token. The session is then pinned to it, so Postgres row-level security
    hides every other tenant's rows even if a query forgets its tenant filter."""
    tenant = db.scalar(select(Tenant).where(Tenant.slug == principal.tenant_slug))
    if tenant is None:
        if principal.via == "oidc":
            raise ForbiddenError(
                f"Your organisation '{principal.tenant_slug}' isn't set up in ufme.", code="unknown_tenant"
            )
        raise NotFoundError(
            f"Tenant '{settings.default_tenant}' has no data. Seed it with `python -m app.seed --force`.",
            code="tenant_not_found",
        )
    if not tenant.is_active:
        raise ForbiddenError(f"{tenant.name} is suspended.", code="tenant_suspended")
    pin_tenant(db, tenant.id)
    return tenant


CurrentTenant = Annotated[Tenant, Depends(current_tenant)]


def current_actor(db: DbSession, tenant: CurrentTenant, principal: CurrentPrincipal) -> Actor:
    """The signed-in person as ufme knows them: role and entity scope come from Administration, not the token."""
    return resolve_actor(db, tenant, principal.email)


CurrentActor = Annotated[Actor, Depends(current_actor)]
