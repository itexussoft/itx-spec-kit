# SaaS platform — domain delivery brief

## When to use

Fill this in when scoping a feature or plan that affects **multi-tenancy, identity, branding, or isolation**. It complements the main spec/plan templates from the base preset.

## Context to capture

- **Tenant model:** Identifier resolution, provisioning, suspension, and data residency if relevant.
- **Isolation:** DB/cache/queue boundaries; RLS, schema-per-tenant, or equivalent; blast radius.
- **Identity:** OIDC/OAuth flows, SSO, IdP federation, token claims used for authorization.
- **Authorization:** How tenant + role + resource checks are enforced consistently (API, jobs, admin).
- **White-label / branding:** Theming, feature flags per tenant, and safe defaults for new tenants.
- **Cross-tenant operations:** What platform admins may do; audit and approval for elevated actions.

## Out of scope (explicit)

- List what this change deliberately does **not** cover to avoid scope creep.

## Risks and open questions

- Record unresolved security, scaling, or tenant-experience risks to resolve before implementation.
