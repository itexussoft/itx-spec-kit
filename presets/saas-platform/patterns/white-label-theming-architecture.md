# White-Label Theming and Runtime Configuration — SaaS Platform

> **Domain:** SaaS Platform  
> **Prerequisite patterns:** `hexagonal-architecture.md`, `federated-identity-oidc.md`

---

## 1. Problem

White-label products need **per-tenant branding** (logos, colors, typography) and **feature availability** without shipping separate frontend builds per customer. **Design tokens** and **feature flags** should be **configuration**, resolved at runtime and cacheable per tenant.

---

## 2. Architecture Overview

```
  Browser / App
       │
       ▼
  ┌─────────────────────────┐
  │  Static shell (CDN)     │  Generic bundle; no tenant secrets
  └────────────┬────────────┘
               │ After auth / tenant resolution
               ▼
  ┌─────────────────────────┐
  │  BFF or Config API      │  GET /tenant-config?version=…
  │                         │  Returns: design tokens, flags, assets URLs
  └────────────┬────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
  ┌─────────┐    ┌──────────────┐
  │ Config  │    │ Object store │
  │ store   │    │ (logos, etc.)│
  │ (DB/    │    │ signed URLs  │
  │  KV)    │    └──────────────┘
  └─────────┘
```

**BFF responsibilities:**

- Authenticate the session (see `federated-identity-oidc.md`).
- Resolve **tenant** from host (custom domain), path, or token claims.
- Return a **versioned** config payload so the client can cache safely (`ETag` / `Cache-Control`).

---

## 3. Design Tokens Pipeline

| Step | Guideline |
|------|-----------|
| **Storage** | Store tokens as JSON or structured rows keyed by `tenant_id` and `schema_version`. |
| **Delivery** | Expose canonical token map to the client; map to CSS variables or theme provider at runtime. |
| **Validation** | Reject unknown token keys in write APIs; constrain color formats to prevent CSS injection. |
| **Defaults** | Fall back to product default theme when tenant config is missing — log and alert for data issues. |

---

## 4. Feature Flags with Tenant Context

- Evaluate flags as `f(tenant_id, user_segment, flag_key)` — never global boolean for tenant-scoped features.
- **Unknown tenant**: default to **off** or safest mode per constitution overlay.
- Audit flag changes per tenant for support and compliance.

---

## 5. Custom Domains

- Map **hostname** → `tenant_id` at the edge (TLS SNI + certificate management).
- Serve the same SPA; config fetch determines branding. Avoid baking tenant into static asset filenames unless using a safe CDN cache key strategy.

---

## 6. Integration with Spec-Kit Workflow

| Phase | Activity |
|-------|----------|
| `/speckit.specify` | List configurable surfaces (theme, flags, copy), custom domain requirements, and cache TTLs. |
| `/speckit.plan` | Design BFF config contract, storage, and CDN strategy. Reference `multi-tenant-data-isolation.md` for config row isolation. |
| `/speckit.tasks` | Separate: config API, admin UI for theme upload, flag service integration, E2E per-tenant theme. |
| `/speckit.implement` | E2E: two tenants, different themes and flag outcomes on same build. |

---

## References

- W3C Design Tokens Community Group (format interoperability).
- See also: `multi-tenant-data-isolation.md`, `federated-identity-oidc.md`.
