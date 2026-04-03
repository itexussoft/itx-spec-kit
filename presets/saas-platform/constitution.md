# SaaS Platform Overlay

## Domain Rules

1. Enforce tenant isolation at every data access layer (database, cache, queues, object storage).
2. Require federated identity (OIDC/OAuth2) with Single Sign-On (SSO) support; do not implement custom token issuance as a substitute for a standards-based IdP.
3. Treat tenant-specific branding and theming configuration as runtime data served via a Backend-for-Frontend (BFF) or configuration API, not as compile-time-only assets.
4. Feature flag evaluation must include tenant context; default to the most restrictive flag state when tenant context is unknown or invalid.

## Architectural Design Requirements

5. During `/speckit.plan`, evaluate `multi-tenant-data-isolation.md`, `federated-identity-oidc.md`, and `white-label-theming-architecture.md` from `.specify/patterns/` for applicability. If the feature reads or writes tenant-scoped data, multi-tenant isolation and tenant context propagation must be justified or explicitly rejected with rationale.
6. The System Design Plan must address tenant isolation strategy in Section 5 (DDD Aggregates) and identity federation / SSO assumptions in Section 9 (Non-Functional Requirements) for any multi-tenant or authenticated user journey.
