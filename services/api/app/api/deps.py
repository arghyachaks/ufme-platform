from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import Tenant

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
