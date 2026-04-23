---
tags:
  - saga
  - transaction
  - compensation
  - orchestrator
  - transfer
  - idempotency
anti_tags:
  - react
  - ui
  - frontend
  - component
  - button
  - toast
  - browser
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Saga — Distributed Transactions for Inter-Account Transfers

> **Domain:** Fintech Banking
> **Prerequisite patterns:** `domain-driven-design.md`,
> `event-driven-microservices.md`, `transactional-outbox.md`

---

## 1. Why Sagas?

A bank transfer debits one account and credits another. When accounts live
in separate Aggregates (or separate services), a single ACID transaction
is impossible without distributed locks that destroy availability. The
Saga pattern replaces the distributed transaction with a sequence of local
transactions coordinated by compensating actions on failure.

---

## 2. Saga Styles

| Style | Description | When to Use |
|-------|-------------|------------|
| **Orchestration** | A central Saga Orchestrator directs each participant step-by-step. | Complex flows with many steps; banking transfers, loan origination. |
| **Choreography** | Each participant listens for events and reacts independently. | Simple 2-3 step flows; lower coupling. |

**Recommendation for banking:** Use **Orchestration** for transfers and
payment flows. The explicit control flow makes regulatory audit and error
handling clearer.

---

## 3. Transfer Saga — Orchestrated Example

### 3.1 Happy Path

```
Orchestrator                 Debit Account         Credit Account
    │                             │                       │
    │── DebitCommand ───────────► │                       │
    │                             │── AccountDebited ──►  │
    │◄── DebitConfirmed ─────────│                       │
    │                             │                       │
    │── CreditCommand ──────────────────────────────────► │
    │                             │                       │── AccountCredited
    │◄── CreditConfirmed ──────────────────────────────── │
    │                             │                       │
    │  (Saga Complete ✓)          │                       │
```

### 3.2 Compensation Path (Credit Fails)

```
Orchestrator                 Debit Account         Credit Account
    │                             │                       │
    │── DebitCommand ───────────► │                       │
    │◄── DebitConfirmed ─────────│                       │
    │                             │                       │
    │── CreditCommand ──────────────────────────────────► │
    │◄── CreditFailed ─────────────────────────────────── │
    │                             │                       │
    │── CompensateDebit ────────► │                       │
    │                             │── DebitReversed       │
    │◄── CompensationConfirmed ──│                       │
    │                             │                       │
    │  (Saga Compensated ✗)       │                       │
```

---

## 4. Saga State Machine

The Orchestrator maintains a persistent state machine:

| State | Description |
|-------|-------------|
| `STARTED` | Saga created, debit command dispatched. |
| `DEBIT_CONFIRMED` | Source account debited; credit command dispatched. |
| `COMPLETED` | Both sides confirmed. Terminal success. |
| `CREDIT_FAILED` | Credit rejected; compensation dispatched. |
| `COMPENSATED` | Debit reversed. Terminal failure. |
| `COMPENSATION_FAILED` | Compensation itself failed. **Requires manual intervention.** Alert on-call immediately. |

- Persist state transitions using the Transactional Outbox
  (see `transactional-outbox.md`) to guarantee delivery of the next
  command even if the orchestrator crashes mid-step.

---

## 5. Idempotency Requirements

Every participant command and compensation must be idempotent:

- `DebitCommand` with the same `saga_id` + `step_id` must produce the same
  result if retried.
- `CompensateDebit` must be safe to call even if the original debit was
  never applied (no-op guard).

---

## 6. Timeout and Escalation

- Each step has a configurable timeout (e.g., 30s for debit confirmation).
- On timeout, the orchestrator retries up to N times, then triggers
  compensation.
- If compensation itself times out, escalate to a dead-letter / manual
  review queue with full saga context attached.

---

## 7. Observability

| Concern | Implementation |
|---------|---------------|
| Saga tracing | Propagate `saga_id` as a correlation header across all commands and events. |
| State visibility | Expose a Saga status API: `GET /sagas/{saga_id}` returning current state + step history. |
| Alerting | Alert on `COMPENSATION_FAILED` state; alert on sagas stuck in non-terminal state beyond SLA. |

---

## 8. Integration with Spec-Kit Workflow

| Phase | Saga Activity |
|-------|--------------|
| `/speckit.specify` | Identify all cross-aggregate operations that require saga coordination. |
| `/speckit.plan` | Draw the Saga state machine. Define compensation logic for each step. Reference this pattern and `transactional-outbox.md` in the System Design Plan. State DDD Aggregates participating. |
| `/speckit.tasks` | Separate: orchestrator state machine, debit participant handler, credit participant handler, compensation handlers, timeout/escalation logic. |
| `/speckit.implement` | Build orchestrator with in-memory stub participants first; integrate real participants; chaos-test compensation paths. |

---

## References

- Hector Garcia-Molina & Kenneth Salem, *Sagas* (1987).
- Chris Richardson, *Microservices Patterns*, Ch. 4 — Sagas.
- See also: `event-sourced-ledger.md`, `transactional-outbox.md`,
  `domain-driven-design.md`.
