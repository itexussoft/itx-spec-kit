# Pattern Index (saas-platform)

## Architectural Patterns
- `multi-tenant-data-isolation.md`: Tenant isolation strategies: RLS, schema-per-tenant, and cache/queue boundaries
- `federated-identity-oidc.md`: OIDC/OAuth2, SSO, IdP federation, and token validation at the API edge
- `white-label-theming-architecture.md`: BFF-served design tokens, feature flags per tenant, and branding isolation

## Code-Level Design Patterns
- `tenant-context-middleware.md`: Resolve and propagate tenant context through HTTP, DB, cache, and messaging

## Anti-Patterns (Forbidden / Demoted)
- `cross-tenant-data-leakage.md`: Forbidden patterns that risk mixing tenant data across isolation boundaries
