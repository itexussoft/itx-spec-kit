# Fintech Banking Overlay

## Domain Rules

1. Preserve ledger invariants and double-entry correctness at all times.
2. Include PSD2 and PCI-aware controls in architecture and implementation plans.
3. Include explicit consent/SCA assumptions for payment-critical workflows.
4. Require auditability and reconciliation for customer-affecting transactions.

## Architectural Design Requirements

5. During `/speckit.plan`, evaluate `event-sourced-ledger.md`, `saga-distributed-transactions.md`, and `psd2-api-gateway.md` from `.specify/patterns/` for applicability. If the feature modifies account balances, event-sourced ledger and saga patterns must be justified or explicitly rejected with rationale.
6. The System Design Plan must address double-entry correctness in Section 5 (DDD Aggregates) and PSD2/PCI compliance in Section 9 (Non-Functional Requirements) for any customer-affecting transaction flow.
