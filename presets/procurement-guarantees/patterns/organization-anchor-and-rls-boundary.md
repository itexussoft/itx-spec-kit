---
tags:
  - orgreference
  - rls
  - tenant
  - isolation
  - schema
  - procurement
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

# Organization Anchor and RLS Boundary

> **Domain:** Procurement Guarantees

Use one party anchor (`OrgReference` or equivalent) to derive visibility for applicants, beneficiaries, issuers, brokers, advisors, and platform actors. Pair application-level scoping with database-level RLS and clear data ownership.

## 1. Architectural Intent

The platform needs one stable party anchor because guarantees are inherently
multi-party. Visibility is not just “tenant vs admin”; it is a matrix across
applicant, beneficiary, issuer, broker, advisor, and platform operator views.

The architectural goal is to derive those views from one party reference model
instead of duplicating access logic in each module.

## 2. Ownership Boundary

Recommended rules:

- writes happen only inside the owning service schema
- reads across schemas are allowed only as explicit projections or read paths
- issuer-scoped and customer-scoped data must never share visibility rules implicitly
- comments, documents, notifications, and snapshots inherit party-scope rules from their owning aggregate
- beneficiary-facing release or presentation data becomes its own visibility surface when exposed externally

## 3. Why it matters

Guarantee platforms routinely mix:

- customer-owned documents
- provider-owned examination notes
- beneficiary-facing undertaking text
- broker or arranger views
- platform-only audit and risk data

Those views overlap, but they do not collapse into one tenant model.

## 4. Views and Entitlements

Keep action permissions separate from read visibility.

- entitlements decide whether a party can submit, approve, release, or examine
- views decide which fields, documents, notes, and projections are visible
- redaction or blurring rules belong to views, not to business transition logic

This distinction is especially useful for broker portals, beneficiary-facing claim
surfaces, and operator tooling where actors may need limited visibility without broad
workflow authority.

## Spec-Kit implications

- Plans must call out org-scope changes whenever a feature touches cross-role visibility.
- Tests must include deny-path scenarios for cross-organization access.
