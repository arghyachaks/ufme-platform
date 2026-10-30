"""Authentication (Stage 5): who is calling, and for which tenant.

Two modes, chosen by `settings.auth_mode`:
- oidc: every call carries `Authorization: Bearer <access token>` issued by the identity provider (Keycloak in
  local Docker; any OIDC provider in the cloud). The token's signature (RS256/ES256, keys from the provider's
  JWKS), issuer, audience and expiry are verified; the email and tenant come from its claims. What the person
  may *do* is decided by ufme (roles and entity scope from the Administration screen), not by the token.
- dev: the X-Ufme-User header names a seeded user. For tests and quick local demos only; refused in prod.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt

from app.core.config import settings
from app.core.errors import AppError

ALGORITHMS = ["RS256", "ES256"]
LEEWAY_S = 30


class AuthError(AppError):
    status_code = 401
    title = "Not signed in"


@dataclass(frozen=True)
class Principal:
    email: str
    tenant_slug: str
    subject: str
    via: str  # "oidc" | "dev"


@lru_cache(maxsize=4)
def _jwks(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True, lifespan=600, timeout=5)


def jwks_url() -> str:
    return settings.oidc_jwks_url or f"{settings.oidc_issuer.rstrip('/')}/protocol/openid-connect/certs"


def verify(token: str, key: Any = None) -> dict[str, Any]:
    """Validated claims of an access token, or AuthError. `key` is for tests (skips the JWKS fetch)."""
    try:
        signing_key = key if key is not None else _jwks(jwks_url()).get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=ALGORITHMS,
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            leeway=LEEWAY_S,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Your session has expired. Sign in again.", code="token_expired") from exc
    except jwt.PyJWKClientError as exc:
        raise AuthError(
            "The sign-in service can't be reached to check your session.", code="idp_unreachable"
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Your sign-in token isn't valid for ufme.", code="invalid_token") from exc


def principal_from_claims(claims: dict[str, Any]) -> Principal:
    email = str(claims.get("email") or claims.get("preferred_username") or "").strip().lower()
    if not email or "@" not in email:
        raise AuthError("Your sign-in token has no email address.", code="no_email_claim")
    tenant = claims.get(settings.oidc_tenant_claim) or settings.default_tenant
    if isinstance(tenant, list):  # Keycloak multivalued attributes arrive as lists
        tenant = tenant[0] if tenant else settings.default_tenant
    return Principal(email=email, tenant_slug=str(tenant), subject=str(claims["sub"]), via="oidc")


def authenticate(authorization: str | None, dev_user: str | None) -> Principal:
    if settings.auth_mode == "oidc":
        scheme, _, token = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthError("Sign in to use ufme.", code="not_authenticated")
        return principal_from_claims(verify(token.strip()))
    if settings.environment == "prod":
        raise AuthError("Developer sign-in is disabled in production.", code="dev_auth_disabled")
    email = (dev_user or settings.demo_user).strip().lower()
    return Principal(email=email, tenant_slug=settings.default_tenant, subject=email, via="dev")
