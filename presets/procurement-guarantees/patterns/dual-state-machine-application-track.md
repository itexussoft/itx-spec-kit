---
tags:
  - lifecycle
  - state-machine
  - application
  - track
  - aggregation
  - procurement
anti_tags:
  - react
  - ui
  - component
  - table
  - modal
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Dual State Machine: Application + Bank Track

> **Domain:** Procurement Guarantees

Use two state machines:

- `Application` for intake, underwriting, and customer-visible progression
- `ApplicationBankTrack` for issuer-specific progression of the undertaking

The platform needs both because underwriting and issuance are not the same lifecycle. A customer application can stay open, be rescored, or be routed to multiple issuers while each issuer track independently moves through review, amendment, issuance, claim, or release.

This mirrors industry practice:

- ICC guidance treats the guarantee lifecycle as multi-stage from drafting through termination.
- SWIFT differentiates issuance (`MT760`), amendment (`MT767`), and demand (`MT765`) rather than collapsing them into one status.

## 1. Architectural Intent

The application lifecycle answers customer-facing questions:

- is the request complete?
- is underwriting still in progress?
- has the platform routed it to providers?

The provider-track lifecycle answers execution questions:

- has a specific issuer accepted the case?
- has an undertaking been issued or amended?
- has a demand been received, examined, paid, rejected, or released?

Those are different consistency boundaries and should not be collapsed into one status column.

## 2. State Ownership

| Aggregate | Owns |
|-----------|------|
| `Application` | intake, readiness, routing intent, overall customer outcome |
| `ApplicationBankTrack` | provider-specific review, issuance, amendment, claim, release |

Once routing begins, the application becomes an aggregate view over provider-track states rather than the sole source of truth for execution.

## 3. Typical Split

| `Application` lifecycle | `ApplicationBankTrack` lifecycle |
|-------------------------|----------------------------------|
| Draft / Submitted | Pending / Routed |
| Underwriting / Rescore | In review / Clarification |
| Ready for issuance | Issued / Active |
| Closed-success / closed-fail | Amended / Claimed / Released / Expired |

## 4. Aggregation Rules

Recommended architectural rule:

- before routing, `Application` is authoritative
- after routing, `Application` is derived from the set of active provider tracks plus terminal-history rules

This allows fan-out, competing offers, partial failures, withdrawals, and claim paths without losing a coherent customer-facing outcome.

## Spec-Kit implications

- Plans must name both affected state machines.
- Tests must cover aggregation rules and terminal-freeze behavior, not just single-entity transitions.

## References

- ICC URDG 758 and related guidance on guarantee lifecycle stages.
- SWIFT Category 7 guarantee issuance/amendment/demand message model.
