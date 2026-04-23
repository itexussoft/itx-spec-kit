---
tags:
  - undertaking
  - message-taxonomy
  - iso20022
  - status
  - notification
  - procurement
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

# Canonical Undertaking Message Taxonomy

> **Domain:** Procurement Guarantees
> **Prerequisite patterns:** `service-domain-semantics-and-contracts.md`, `snapshot-evidence-boundary.md`

Model partner and provider exchanges using a canonical undertaking message taxonomy. Preserve the difference between requests, operative messages, advice, notification, response, and status reporting instead of collapsing them into a generic "update" event.

This pattern draws on ISO 20022 Trade Services `tsrv` message families for undertakings and demand handling.

## 1. Architectural Intent

Procurement-guarantee integrations fail when the platform represents every external
exchange as a single status mutation or a generic document upload. Real undertaking
operations carry different semantics:

- a request asks for a change
- an issuance or amendment message carries operative content
- an advice informs another party of what was issued or changed
- a notification reports that something happened
- a response accepts, rejects, or records a position
- a status report communicates state plus reason

Those message families should remain distinct in the domain model, event model, and
evidence trail.

## 2. Canonical Message Families

Recommended semantic families:

| Family | Typical examples |
|--------|-------------------|
| Issuance | issuance request, issuance message, issuance advice, issuance notification |
| Amendment | amendment request, amendment message, amendment advice, amendment response, amendment response notification |
| Demand / Claim | demand presentation, extend-or-pay request, extend-or-pay response, demand refusal notification, demand withdrawal notification |
| Termination | non-extension request, non-extension notification, termination notification, release notice |
| Status | undertaking status report, trade status report, status advice with reasons |
| Evidence envelope | attached documents, document types, formats, digital signatures, copies or duplicates, message definition identifiers |

The platform may not need each family in every rollout, but it should preserve the
taxonomy so new providers and channels fit without redesigning the model.

## 3. Status Semantics

Status reporting must be richer than a single code.

Recommended architecture:

- status category for the broad lifecycle bucket
- status code for the concrete state
- status reasons for explanation, exception, or operational detail
- message identifiers for traceability across external and internal flows

This mirrors ISO 20022 status reports and reduces the temptation to encode all nuance
into one overloaded application status field.

## 4. Documentary and Presentation Semantics

ISO 20022 trade-services schemas reinforce that undertaking flows are document-aware.
The architecture should therefore preserve:

- document type
- document format
- digital signature metadata
- presentation medium
- place of presentation
- copy or duplicate markers where message provenance matters

These are not transport trivia. They often determine operational routing, evidence
reproducibility, and claim-examination correctness.

## 5. Boundary Rules

Recommended rules:

- provider and network adapters map raw payloads into canonical message families
- internal workflows operate on semantic message intents, not raw transport types
- status reports append evidence and reasons rather than mutating prior messages in place
- request, advice, notification, and response semantics remain queryable in history and audit views

Do not normalize away meaning that matters to claim handling, dispute review, or
partner reconciliation.

## Spec-Kit implications

- `/speckit.plan`: identify whether the change introduces a request, operative message, advice, notification, response, or status report.
- `/speckit.plan`: describe the canonical message family and the evidence it must retain.
- `/speckit.tasks`: separate adapter mapping, canonical eventing, status-reason handling, and evidence persistence.
- `/speckit.implement`: preserve replayable history of message families and status reasons.

## References

- ISO 20022 Trade Services `tsrv` message families for undertaking issuance, amendment, demand, termination, and status reporting.
- SWIFT Category 7 lifecycle semantics for issuance, amendment, demand, and related notifications.
