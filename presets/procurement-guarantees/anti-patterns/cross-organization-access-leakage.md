---
tags:
  - org
  - access
  - leakage
  - rls
  - principal
  - bank
  - broker
anti_tags:
  - react
  - ui
  - component
  - branding
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Anti-Pattern: Cross-Organization Access Leakage

> **Domain:** Procurement Guarantees
> **Severity:** MUST NOT — breaks confidentiality, provider segregation, and beneficiary trust.
> **Remedy:** Explicit party scoping, request-scoped context, RLS, and role-aware repositories.

---

## 1. Definition

**Cross-organization access leakage** happens when one party can view or mutate
another party's applications, undertakings, claim packages, notes, or
notifications because scope is inferred implicitly or not enforced end-to-end.

Typical examples:

- broker sees issuer-only examination notes
- issuer sees another issuer's competing undertaking track
- applicant sees beneficiary-only claim documents
- global cache key returns another tenant's document metadata

---

## 2. Why It Is Forbidden

| Problem | Consequence |
|---------|-------------|
| Mixed visibility between applicant, issuer, beneficiary, broker, and operator | Confidential commercial data leaks across parties. |
| UI-only access checks | API or async jobs can bypass the intended boundary. |
| Shared cache or bucket namespace | One party can resolve another party's documents or status by key collision. |
| Missing provider isolation | Competing issuers can see each other's pricing, underwriting, or claim actions. |

---

## 3. Common Violations

| Violation | Example |
|-----------|---------|
| Query by `application_id` only | `SELECT * FROM documents WHERE application_id = :id` without party scope |
| Global cache key | `cache.get("application:123")` |
| Trusting client role header | `X-Party-Type: bank` accepted without verified subject context |
| Shared object-store prefix | `/documents/{application_id}/...` without issuer or owner namespace |

---

## 4. Detection Checklist

The AI agent must flag code when:

- [ ] Provider- or party-facing queries omit `org_ref_id`, `tenant_id`, or equivalent scope.
- [ ] Cache keys do not include party namespace.
- [ ] Controller or webhook logic trusts client-supplied role or organization values directly.
- [ ] Repository methods return “all tracks/documents for application” without caller scope.

---

## 5. Correct Alternative

- Resolve the caller's party context once per request.
- Propagate that context to repositories, caches, queues, and object storage.
- Keep RLS or equivalent database controls as defense in depth.
- Distinguish `platform-admin`, `operator`, `issuer`, `broker`, `beneficiary`, and `applicant` views explicitly.

---

## 6. AI Agent Enforcement Rules

1. **NEVER** rely on UI routing or screen ownership to enforce access.
2. **ALWAYS** include explicit party scope in repository and storage access.
3. **ALWAYS** namespace cache and object-store keys by party or tenant.
4. **NEVER** expose competing issuer tracks to another issuer unless there is an explicit shared-market requirement.
