---
tags:
  - exposure
  - limit
  - collateral
  - utilization
  - amount
  - expiry
anti_tags:
  - react
  - ui
  - component
  - chart
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Exposure Ledger and Limit Management

> **Domain:** Procurement Guarantees

Guarantee platforms need more than workflow state. They also need a view of outstanding obligation exposure by applicant, issuer, facility, currency, and expiry.

## 1. Architectural Intent

Every issued undertaking consumes some combination of:

- issuer facility or underwriting capacity
- collateral or cash cover
- country, sector, or beneficiary concentration
- operational follow-up through expiry or release

A workflow-only model misses core risk questions such as:

- How much exposure is still outstanding?
- Which guarantees have reduced amounts over time?
- Which undertakings should auto-expire versus require explicit release?
- Which applicants are near issuer limits?

## 2. Architectural Separation

Separate:

- **workflow state**: where the request is in the process
- **undertaking state**: whether the guarantee is active, amended, released, expired
- **exposure state**: what financial or contingent obligation is still outstanding

Exposure is not just another UI field on the undertaking. It is a reporting and risk boundary with its own projections and controls.

## 3. Recommended Read Models

| Read model | Purpose |
|-----------|---------|
| Applicant utilization | Outstanding amount by applicant and facility |
| Expiry ladder | Guarantees grouped by expiry window |
| Collateral position | Cash cover and collateral linked to undertakings |
| Claims book | Open and paid demands |

## 4. Recommended Event Sources

Typical exposure-changing events:

- undertaking issued
- amount reduced
- amendment increased amount or extended expiry
- claim paid or reserved
- release confirmed
- expiry reached

Architecturally, these events should feed a rebuildable exposure view rather than mutate one opaque balance field.

## 4. Spec-Kit implications

- `/speckit.plan`: state whether the feature changes exposure semantics, not just user workflow.
- `/speckit.tasks`: separate exposure-write logic, projections, and reporting.
- `/speckit.implement`: verify reduction, release, and claim effects on outstanding balances.

## References

- World Bank procurement forms showing reduction and expiry semantics for advance-payment and performance securities.
