# Local sign-in (Keycloak)

The local stack runs [Keycloak](https://www.keycloak.org/) (open source, Apache 2.0) as the OIDC identity
provider. `ufme-realm.json` is imported on first start:

- realm `ufme`, browser client `ufme-web` (public, Authorization Code + PKCE S256)
- access tokens carry audience `ufme-api` and claim `ufme_tenant=demo`
- the sign-in pages use the `ufme` theme in `themes/ufme` (restyled keycloak.v2: same look as the app)
- the seeded demo users (`priya.nair@example.com`, `daniel.ortiz@example.com`, ...), all with the
  development password `ufme-demo`; `tom.becker` is disabled

**Development only.** The realm, passwords and the admin console login (`admin`, see `KC_BOOTSTRAP_ADMIN_*` in
the compose file) are for a laptop. In the cloud, point `OIDC_ISSUER` / `OIDC_JWKS_URL` / `OIDC_AUDIENCE` at the
real provider (Keycloak, Entra ID, Okta, ...) and set secrets from the secret store.

Keycloak decides *who* someone is. *What* they may do (role, entities) is managed in ufme's Administration
screen; an identity that isn't a ufme user in that tenant gets 403.

- Sign-in page: http://localhost:8081/realms/ufme/account
- Admin console: http://localhost:8081/admin
