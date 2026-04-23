---
tags:
  - ledger
  - transaction
  - reconciliation
  - event-sourcing
  - account
anti_tags:
  - react
  - ui
  - frontend
  - component
  - toast
  - browser
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Event-Sourced Ledger — Fintech Banking

> **Domain:** Fintech Banking
> **Prerequisite patterns:** `domain-driven-design.md`, `hexagonal-architecture.md`

---

## 1. Why Event Sourcing for a Ledger?

A financial ledger's primary invariant is **immutability** — once a
transaction is recorded, it can never be silently altered. Traditional
CRUD overwrites state, making audit reconstruction difficult and
regulatory compliance brittle. Event Sourcing stores every state change
as an immutable, append-only event, making the ledger a first-class
audit trail by construction.

---

## 2. Core Concepts

### 2.1 Event Store

The Event Store is the system of record. It persists an ordered sequence
of events per Aggregate (the `Account` Aggregate in banking).

```sql
CREATE TABLE account_events (
    event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_id    UUID         NOT NULL,       -- account ID
    sequence_number BIGINT       NOT NULL,        -- per-aggregate monotonic
    event_type      VARCHAR(255) NOT NULL,
    payload         JSONB        NOT NULL,
    metadata        JSONB        NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (aggregate_id, sequence_number)
);
```

- **Append-only**: no `UPDATE` or `DELETE` on this table. Ever.
- **Optimistic concurrency**: load the current `sequence_number` before
  appending; reject if another writer incremented it first.

### 2.2 Account Aggregate

The `Account` Aggregate Root is reconstituted by replaying its event
stream:

```
AccountOpened → FundsDeposited → FundsWithdrawn → FundsDeposited → ...
                 ▼ replay ▼
              Account { balance: 1500.00, status: Active }
```

**Domain Events (examples):**

| Event | Key Fields |
|-------|-----------|
| `AccountOpened` | `account_id`, `owner_id`, `currency`, `opened_at` |
| `FundsDeposited` | `amount`, `source_reference`, `value_date` |
| `FundsWithdrawn` | `amount`, `destination_reference`, `value_date` |
| `AccountFrozen` | `reason`, `frozen_by` |
| `AccountClosed` | `closed_at`, `final_balance` |

### 2.3 Snapshots

Replaying thousands of events is expensive. Periodically persist a
**snapshot** of the Aggregate state:

- Store snapshots in a separate table keyed by `(aggregate_id, snapshot_version)`.
- On load: fetch the latest snapshot, then replay only events with
  `sequence_number > snapshot_version`.
- Snapshot frequency: every N events (e.g., 100) or on a schedule.

---

## 3. Projections (Read Models)

Event-sourced systems rely on projections for queries:

| Projection | Purpose | Storage |
|-----------|---------|---------|
| Account Balance | Real-time balance lookups | PostgreSQL materialized view or Redis |
| Transaction History | Customer-facing statement | Elasticsearch or read-replica table |
| Reconciliation Ledger | Daily double-entry reconciliation | Append-only reporting table |
| Regulatory Reporting | Suspicious activity monitoring | Data warehouse / SIEM feed |

Projections are rebuilt from the event stream — they are disposable and
can be recreated at any time.

---

## 4. Double-Entry Bookkeeping

Every `FundsDeposited` or `FundsWithdrawn` event on one account must have
a corresponding contra-entry on another account (or an external
settlement account). The Saga pattern (see `saga-distributed-transactions.md`)
orchestrates cross-account transfers to maintain double-entry correctness.

---

## 5. Regulatory and Audit Considerations

| Requirement | How Event Sourcing Satisfies It |
|------------|-------------------------------|
| Tamper evidence | Append-only store; compute a hash chain over events for integrity verification. |
| Point-in-time reconstruction | Replay events up to any timestamp to reconstruct past state. |
| Audit trail | Events **are** the audit trail — no separate logging needed. |
| Data retention | Archive old events to cold storage; snapshots allow pruning if regulations permit. |

---

## 6. Integration with Spec-Kit Workflow

| Phase | Event-Sourced Ledger Activity |
|-------|------------------------------|
| `/speckit.specify` | Define the Account Aggregate's event catalog. State which events are externally published (Integration Events). |
| `/speckit.plan` | Choose Event Store technology (EventStoreDB, PostgreSQL, DynamoDB). Define snapshot strategy. Define projections. Reference this pattern in the System Design Plan. State DDD Aggregates explicitly. |
| `/speckit.tasks` | Separate: event store schema, Aggregate replay logic, snapshot mechanism, each projection, reconciliation job. |
| `/speckit.implement` | Build event store adapter first; implement Aggregate replay; add projections; run reconciliation smoke tests. |

---

## References

- Greg Young, *Event Sourcing* (2010).
- Martin Fowler, *Event Sourcing* (bliki).
- See also: `domain-driven-design.md`, `saga-distributed-transactions.md`,
  `transactional-outbox.md`.
