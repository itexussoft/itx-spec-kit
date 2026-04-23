---
tags:
  - tenant
  - leakage
  - isolation
  - cache
  - query
  - header
  - tenant_id
anti_tags:
  - react
  - ui
  - frontend
  - component
  - theme
  - theming
  - branding
  - logo
  - color
  - typography
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Cross-Tenant Data Leakage — Anti-Pattern

> **Domain:** SaaS Platform  
> **Related patterns:** `multi-tenant-data-isolation.md`, `tenant-context-middleware.md`

---

## 1. Status

**Guard** — violations are high-severity security defects. Any use in new code must be rejected in review; legacy code must be remediated with explicit isolation controls.

---

## 2. Forbidden Patterns

| Anti-pattern | Why it fails |
|--------------|--------------|
| **Queries without tenant filter** | ORM `Model.objects.all()` or raw SQL without `WHERE tenant_id = :tid` risks returning all tenants’ rows. |
| **Global cache keys** | `cache.get("user:123")` shared across tenants lets tenant A read tenant B’s cached profile if IDs collide or remap. |
| **Trusting client tenant header alone** | Spoofed `X-Tenant-Id` from an anonymous client must never select data without cryptographic trust (JWT) or gateway stripping. |
| **Logging tenant A payload in tenant B request** | Copy-paste logging of full objects without scoping can leak data across support sessions. |
| **Singleton services holding “current tenant”** | Mutable global “current tenant” breaks under concurrency; use request-scoped context only. |
| **Admin “switch tenant” without audit** | Impersonation or support views must log every access with actor, tenant, and reason. |

---

## 3. Required Mitigations

- **Defense in depth:** application filters **plus** RLS (or equivalent) where the database supports it.
- **Key namespaces:** all cache and object-store paths include tenant segment.
- **Automated tests:** contract tests that attempt cross-tenant ID access and expect deny or empty.

---

## 4. Spec-Kit / Plan Alignment

- In System Design Plan Section 4b, mark this anti-pattern **Guard** when the feature touches tenant data; document mitigations (middleware, RLS, tests).

---

## References

- OWASP Multi-Tenancy Cheat Sheet (tenant isolation concepts).
- See also: `multi-tenant-data-isolation.md`.
