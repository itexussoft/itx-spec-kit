---
tags:
  - cqrs
  - order
  - sequencing
  - command
  - aggregate
  - projection
  - outbox
anti_tags:
  - react
  - ui
  - frontend
  - component
  - table
  - grid
  - modal
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

# CQRS with Order Sequencing — Fintech Trading

> **Domain:** Fintech Trading
> **Prerequisite patterns:** `domain-driven-design.md`, `hexagonal-architecture.md`

---

## 1. Why CQRS for Trading?

Trading engines face an asymmetric workload: writes (order placement,
amendment, cancellation) demand sub-millisecond latency and strict
sequencing, while reads (order book snapshots, position queries, P&L
dashboards) demand high throughput and flexible projections. CQRS
separates these concerns into distinct models.

---

## 2. Command Side — Write Model

### 2.1 Order Aggregate

The `Order` Aggregate Root enforces the order lifecycle state machine:

```
  New → Pending → PartiallyFilled → Filled
         │              │
         └──► Cancelled ◄──┘
         │
         └──► Rejected
```

**Invariants enforced inside the Aggregate:**

- An order may only be cancelled if not fully filled.
- Fill quantity must not exceed remaining quantity.
- Amendment is only valid in `Pending` or `PartiallyFilled` states.
- Every state transition emits a domain event (`OrderPlaced`,
  `OrderAmended`, `OrderPartiallyFilled`, `OrderFilled`,
  `OrderCancelled`, `OrderRejected`).

### 2.2 Sequencing

- Every command carries a **sequence number** assigned by the gateway at
  ingress (monotonically increasing per session).
- The command handler rejects out-of-sequence commands with a `SequenceGap`
  error to prevent reordering.
- Within the Aggregate, an **optimistic concurrency version** guards against
  lost updates under concurrent matching-engine callbacks.

### 2.3 Command Processing Pipeline

```
Gateway (assigns seq#) → Command Bus → Command Handler → Order Aggregate
                                                             │
                                                   Domain Events
                                                             │
                                                  Transactional Outbox
```

- Use the Transactional Outbox (see `transactional-outbox.md`) to guarantee
  events reach the read-model projector and downstream consumers.

---

## 3. Query Side — Read Model

### 3.1 Projections

| Projection | Storage | Updated By |
|-----------|---------|-----------|
| Order Book (L2/L3) | In-memory or Redis sorted set | `OrderPlaced`, `OrderFilled`, `OrderCancelled` events |
| Position & P&L | Columnar store / TimescaleDB | `OrderFilled` + market data ticks |
| Order History | Elasticsearch / PostgreSQL | All order lifecycle events |

### 3.2 Consistency Guarantees

- Read models are **eventually consistent** with the write model.
- Publish the write model's event version alongside projections so clients
  can detect stale reads (e.g., `X-Event-Version` header).
- For latency-critical reads (e.g., order status polling during matching),
  allow a direct read-through to the write-model database as a fallback,
  but document this as a conscious trade-off.

---

## 4. Latency Considerations

| Concern | Guideline |
|---------|-----------|
| Serialization | Use binary formats (FlatBuffers, SBE) for command/event payloads on the hot path. JSON/Protobuf for non-latency-critical projections. |
| Persistence | Write-model DB should be co-located (same AZ) with the command handler. |
| GC pressure | Prefer object pooling and pre-allocated buffers in the matching-engine loop. |
| Event relay | CDC-based outbox relay for sub-10ms event propagation; polling is too slow for trading. |

---

## 5. Integration with Spec-Kit Workflow

| Phase | CQRS Activity |
|-------|--------------|
| `/speckit.specify` | Define command set and event set for the Order Aggregate. List read-model projections. |
| `/speckit.plan` | Choose projection stores. Define latency SLOs. Reference this pattern and `transactional-outbox.md` in the System Design Plan. State the DDD Aggregate explicitly. |
| `/speckit.tasks` | Separate: command-side Aggregate + handler, outbox relay, each projection, API gateway sequencing. |
| `/speckit.implement` | Build command side first; add projections incrementally; measure latency against SLOs in integration tests. |

---

## References

- Greg Young, *CQRS Documents* (2010).
- Martin Fowler, *CQRS* (bliki).
- See also: `domain-driven-design.md`, `transactional-outbox.md`,
  `high-availability-cell-based.md`.
