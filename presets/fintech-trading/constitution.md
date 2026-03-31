# Fintech Trading Overlay

## Domain Rules

1. Enforce strict order lifecycle correctness and deterministic state transitions.
2. Require idempotency and sequencing safeguards for externally visible operations.
3. Preserve auditability and reconciliation metadata for all order-affecting operations.
4. Never use floating-point primitives for monetary calculations.

## Architectural Design Requirements

5. During `/speckit.plan`, evaluate `cqrs-order-sequencing.md` and `high-availability-cell-based.md` from `.specify/patterns/` for applicability to the feature. If the feature involves order flow, CQRS with order sequencing must be justified or explicitly rejected with rationale.
6. The System Design Plan must include latency SLOs in Section 9 (Non-Functional Requirements) for any order-affecting operation.

## Performance Context

- Explicitly document latency constraints and SLO assumptions in implementation plans.
