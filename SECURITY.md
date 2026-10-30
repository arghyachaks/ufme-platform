# Security policy

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Use GitHub's
[private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
on this repository (Security tab → "Report a vulnerability").

Include what you found, how to reproduce it, and the impact you expect. You'll get an acknowledgement within
7 days. Please give a reasonable time to fix before disclosing publicly.

## Scope

The local Docker stack is configured for development: the Keycloak realm,
demo users and passwords, and the default evidence-signing key are **for local use only** and must be replaced
before any real deployment (see `infra/keycloak/README.md`).

In scope: authentication and authorization bypass, cross-tenant data access, audit-trail tampering, injection,
secrets exposure. Findings that only apply to the documented development defaults are out of scope.

## Supported versions

Only the latest commit on the default branch receives fixes.
