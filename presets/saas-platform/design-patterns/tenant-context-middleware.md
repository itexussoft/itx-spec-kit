---
tags:
  - tenant
  - context
  - middleware
  - propagation
  - request
  - session
  - header
anti_tags:
  - react
  - ui
  - frontend
  - component
  - provider
  - hook
  - theme
  - modal
  - browser
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Tenant Context Middleware — Resolve and Propagate Tenant Scope

> **Domain:** SaaS Platform  
> **Prerequisite patterns:** `decorator-middleware.md`, `multi-tenant-data-isolation.md`

---

## 1. Intent

Provide a **single, consistent** way to resolve **which tenant** the current request or job belongs to and to propagate that context to databases, caches, queues, and logs — without leaking one tenant’s scope into another’s.

---

## 2. Resolution Order

Typical precedence (configure per product):

1. **Custom domain** → lookup `tenant_id` in domain registry.
2. **Path prefix** → `/t/{tenant_slug}/...` (B2B consoles).
3. **JWT / session claim** → trusted `tenant_id` or `org_id` from validated token.
4. **Header** → e.g. `X-Tenant-Id` only when combined with **authenticated** gateway trust (never alone from anonymous clients).

The middleware **sets** an immutable **request-scoped context** object (e.g. context var, DI scope) containing at minimum:

- `tenant_id` (internal UUID or stable string)
- Optional: `tenant_slug`, `region`, `plan_tier`

---

## 3. Propagation Checklist

| Destination | Mechanism |
|-------------|-----------|
| **PostgreSQL RLS** | `SET app.tenant_id = '...'` per connection checkout or session variable via pool hook. |
| **ORM queries** | Repository base class requires `tenant_id` filter for tenant-scoped entities; RLS as defense in depth. |
| **Redis / Memcached** | Prefix keys: `t:{tenant_id}:{entity}:{id}`. |
| **Message bus** | Add `tenant_id` to message envelope; consumer validates before handling. |
| **Structured logs** | Include `tenant_id` as a field; never log secrets or PII beyond policy. |

---

## 4. Structure (Conceptual)

```
Request ──► TenantResolveMiddleware ──► AuthMiddleware ──► Handler
                    │                         │
                    └─► TenantContext         └─► User + roles within tenant
                         (request scope)
```

- **Order matters:** authenticate before trusting tenant claims; for domain-based resolution, validate the user is a member of the resolved tenant.

---

## 5. Background Jobs

- Scheduled jobs must receive `tenant_id` in the job payload.
- **Fan-out** pattern: a scheduler enqueues one job per tenant for tenant-scoped work — avoids a global “process all tenants” without explicit iteration.

---

## 6. Testing

- Unit tests: middleware sets context from mocked request.
- Integration tests: two tenants, same endpoint, assert row counts and 403/404 when crossing tenants.

---

## References

- See also: `multi-tenant-data-isolation.md`, `cross-tenant-data-leakage.md`.
