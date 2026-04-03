# SaaS Platform Glossary

- **Tenant**: A customer or organization whose data and configuration are isolated from other tenants.
- **Tenant context**: The resolved tenant identifier and related attributes (plan, region, IdP mapping) carried through a request or job.
- **Design token**: A named, versioned design value (color, spacing, typography) resolved at runtime for white-label UIs.
- **Feature flag**: A toggled capability evaluated per tenant (and optionally per user or segment).
- **OIDC**: OpenID Connect — identity layer on OAuth2 for authentication and ID tokens.
- **OAuth2**: Authorization framework for delegated access; often paired with OIDC for login.
- **PKCE**: Proof Key for Code Exchange — required for public OAuth clients and recommended for SPA/mobile flows.
- **IdP**: Identity Provider — the system that authenticates users and issues tokens (enterprise SSO, social login, etc.).
- **SCIM**: System for Cross-domain Identity Management — provisioning users/groups into the application from an IdP.
- **SSO**: Single Sign-On — users sign in once at an IdP and access multiple applications without re-entering credentials.
- **White-label**: Per-tenant branding, domains, and UX configuration without separate codebases.
- **Noisy neighbor**: One tenant’s load or queries degrading performance for others on shared infrastructure.
- **Row-Level Security (RLS)**: Database-enforced row filters so queries only see rows for the current tenant context.
- **Tenant isolation level**: The strength of separation (shared DB + RLS, schema-per-tenant, database-per-tenant, etc.).
