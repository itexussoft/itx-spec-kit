---
tags:
  - flow
  - metamodel
  - configuration
  - flowversion
  - procurement
  - guarantee
anti_tags:
  - react
  - ui
  - component
  - modal
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Configurable Flow Metamodel — Procurement Guarantees

> **Domain:** Procurement Guarantees
> **Prerequisite patterns:** `domain-driven-design.md`, `hexagonal-architecture.md`

Model guarantee products as `FlowDefinition` + `FlowVersion`, not as hardcoded branches per issuer, country, or procurement regime. The same platform core should support bid bonds, performance guarantees, advance-payment guarantees, payment bonds, maintenance bonds, and local variants through configuration and versioning.

International practice reinforces this approach:

- ICC URDG 758 describes a stage-by-stage guarantee lifecycle rather than a single local workflow.
- World Bank procurement forms use demand guarantees across bid, performance, and advance-payment securities.
- Surety markets distinguish multiple contract-bond products under the same core tripartite model.

## 1. Architectural Intent

Guarantee platforms vary along several dimensions:

- product class
- party topology
- documentary requirements
- claim conditions
- release rules
- provider/network capabilities

Hardcoding those variations in services produces a brittle matrix of `if country == ...`, `if bank == ...`, and `if product == ...` branches. A metamodel keeps the platform extensible while preserving a stable core.

## 2. Architectural Shape

Separate the platform into:

- **product template model**: what kind of undertaking this is
- **runtime application model**: one concrete customer or broker request
- **provider-track model**: one issuer- or surety-specific execution path
- **policy/version model**: underwriting, evidence, and lifecycle rules active at a point in time

The architectural rule is simple: product variability lives in templates and policy versions, while runtime services execute against one immutable version binding.

## 3. Recommended Model Slices

| Slice | Examples |
|-------|----------|
| Product template | Bid bond, performance guarantee, advance-payment guarantee |
| Party topology | Applicant, beneficiary, issuer, counter-guarantor, broker |
| Evidence rules | Required docs for issuance, amendment, claim, release |
| Commercial rules | Amount, currency, reduction schedule, expiry policy |
| Network rules | Portal, API, SWIFT, file exchange |
| Claim rules | On-demand, documentary, extend-or-pay, release confirmation |

## 4. Context Boundaries

Typical bounded contexts in this architecture:

| Context | Owns |
|---------|------|
| Product Configuration | Flow definitions, versions, publication lifecycle |
| Application Intake | Applicant request, collected data, submission lifecycle |
| Underwriting / Recommendation | Screening, scoring, provider fit, recommendation history |
| Undertaking Execution | Issuer tracks, issuance, amendment, claim, release |
| Evidence / Documents | Versioned documentary artifacts and signatures |

The pattern works best when those contexts collaborate through explicit version references and immutable snapshots rather than shared mutable state.

## Spec-Kit implications

- `/speckit.plan`: state whether the feature changes product templates, runtime behavior, or both.
- `/speckit.tasks`: separate metamodel changes from runtime service changes, migrations, and provider/adaptor work.
- `/speckit.implement`: preserve deterministic reads for old applications after a new flow version is published.

## References

- ICC URDG 758 lifecycle guidance and commentary.
- World Bank standard procurement forms for bid, performance, and advance-payment guarantees.
- NASBP contract surety product taxonomy.
