---
tags:
  - snapshot
  - evidence
  - document
  - history
  - versioning
  - audit
anti_tags:
  - react
  - ui
  - component
  - upload-widget
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Snapshot Evidence Boundary

> **Domain:** Procurement Guarantees

When sending or advising a guarantee package, preserve what was actually sent. Runtime application data may continue evolving, but each issuer track must expose a reproducible trail of:

- application data used for the decision
- undertaking wording and amendments
- supporting documents
- claims/presentations
- release or expiry evidence

## 1. Architectural Intent

Guarantee systems are documentary systems. They need a stable evidence boundary
between mutable application data and immutable provider-facing or
beneficiary-facing packages.

This pattern defines that boundary.

## 2. Evidence Boundary Rules

- capture `INITIAL` snapshots on first delivery or first binding decision handoff
- capture `UPDATE` snapshots for clarification, amendment, or additional-document rounds
- keep `DocumentVersion`, track snapshots, claim presentations, message exchanges, and status history append-only
- model the issued undertaking, amendment text, and release evidence as versioned documentary artifacts
- preserve message-definition identifiers, document types, document formats, digital signatures, and copy or duplicate markers when they exist in provider exchanges
- retain enough evidence to answer: what was issued, what was amended, what was demanded, what was examined, what was paid or released

## 3. Why it matters

- ICC guarantee practice is document- and presentation-centric.
- World Bank-style forms require guarantee text, amounts, expiry, reduction, and beneficiary statements to be reproducible.
- Fraud review, dispute handling, and provider escalation depend on historical evidence, not just current state.

## 4. Evidence Classes

| Evidence class | Example |
|----------------|---------|
| Underwriting snapshot | Documents and data used before issuance |
| Issuance package | Undertaking wording, amount, expiry, beneficiary |
| Amendment evidence | Changed text, changed amount, changed expiry |
| Presentation package | Demand statement plus supporting docs |
| Termination evidence | Expiry confirmation, return, release, cancellation |
| Message evidence | Advice, notification, response, status report with identifiers and reasons |

## 5. Read/Write Implications

Recommended architecture:

- writes create new evidence artifacts
- reads assemble historical packages for issuer, beneficiary, operator, and audit views
- projections may optimize retrieval, but the source evidence remains immutable

## Spec-Kit implications

- Any feature changing provider-facing data must state whether new snapshots are created, reused, or merely read.
- Acceptance tests must verify the provider or beneficiary sees the correct historical package even after the application changes again.

## References

- ICC URDG 758 guidance on complying presentation and lifecycle handling.
- SWIFT usage rules separating issuance, amendment, and demand messages.
