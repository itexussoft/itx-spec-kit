---
tags:
  - transaction
  - outbox
  - event
  - broker
  - database
  - relay
anti_tags:
  - react
  - ui
  - frontend
  - component
  - button
  - click
  - toast
  - browser
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Transactional Outbox

> **Applicability:** Any service that must atomically update its database
> **and** publish a domain/integration event. Prevents the dual-write
> problem that leads to silent data loss or ghost events.

---

## 1. The Dual-Write Problem

When a service writes to a database and then publishes an event to a message
broker in two separate operations, either can fail independently:

- DB commits but event publish fails → downstream services never learn about
  the change (data loss).
- Event publishes but DB commit fails → downstream services act on a change
  that never happened (ghost event).

**The Transactional Outbox eliminates this by making event publishing part
of the database transaction.**

---

## 2. How It Works

```
┌─────────── Service ───────────┐
│                                │
│  1. Begin DB Transaction       │
│  2. Mutate Aggregate table     │
│  3. INSERT into outbox table   │
│  4. Commit Transaction         │
│                                │
└────────────┬───────────────────┘
             │
             │  (async relay process)
             ▼
┌──────────────────────────────────┐
│  Outbox Relay / CDC Connector    │
│  Reads committed outbox rows     │
│  Publishes to message broker     │
│  Marks rows as published         │
└──────────────────────────────────┘
             │
             ▼
      [ Message Broker ]
```

### 2.1 Outbox Table Schema

```sql
CREATE TABLE outbox (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_type VARCHAR(255) NOT NULL,
    aggregate_id   VARCHAR(255) NOT NULL,
    event_type     VARCHAR(255) NOT NULL,
    payload        JSONB        NOT NULL,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    published_at   TIMESTAMPTZ           DEFAULT NULL
);
```

- `published_at IS NULL` → not yet relayed.
- The relay sets `published_at` after successful broker acknowledgment.

### 2.2 Relay Strategies

| Strategy | Description | Trade-off |
|----------|-------------|-----------|
| **Polling Publisher** | A scheduled job queries `WHERE published_at IS NULL` and publishes in batches. | Simple; adds publish latency equal to poll interval. |
| **Change Data Capture (CDC)** | Debezium / AWS DMS tails the DB WAL and streams outbox inserts directly to Kafka. | Near-real-time; operationally heavier. |
| **Transaction Log Tailing** | Custom log reader for databases that expose a change stream (e.g., MongoDB Change Streams). | Database-specific. |

---

## 3. Ordering Guarantees

- Outbox rows for the same `aggregate_id` must be published in insertion
  order (use the `created_at` + row ID for deterministic ordering).
- Route events for the same aggregate to the same broker partition (partition
  key = `aggregate_id`) to preserve per-aggregate ordering downstream.

---

## 4. Exactly-Once Semantics

The Outbox guarantees at-least-once publishing. Combined with idempotent
consumers (see `event-driven-microservices.md`), the system achieves
effective exactly-once processing.

---

## 5. Cleanup

Outbox rows are transient infrastructure data. Purge published rows on a
schedule (e.g., retain 7 days, then archive or delete).

---

## 6. Integration with Spec-Kit Workflow

| Phase | Outbox Activity |
|-------|----------------|
| `/speckit.plan` | Declare which Aggregates require outbox publishing. Choose relay strategy (polling vs. CDC). Reference this pattern in the System Design Plan. |
| `/speckit.tasks` | Task 1: outbox table migration. Task 2: outbox write in Aggregate repository. Task 3: relay process implementation. |
| `/speckit.implement` | The repository adapter inserts outbox rows in the same transaction as aggregate mutations. Never publish events outside this mechanism. |

---

## References

- Chris Richardson, *Microservices Patterns*, Ch. 3 — Transactional Outbox.
- Gunnar Morling, *Reliable Microservices Data Exchange With the Outbox Pattern* (Debezium blog).
- See also: `event-driven-microservices.md`, `domain-driven-design.md`.
