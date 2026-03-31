# High-Availability Cell-Based Architecture — Fintech Trading

> **Domain:** Fintech Trading
> **Prerequisite patterns:** `event-driven-microservices.md`, `domain-driven-design.md`

---

## 1. Motivation

A trading platform cannot afford correlated failures. A single bad
deployment, database migration, or infrastructure fault must not take down
the entire order flow. Cell-based architecture contains the **blast radius**
of any failure to a single cell, preserving availability for all other
cells.

---

## 2. What Is a Cell?

A **cell** is a fully self-contained, independently deployable replica of
the trading engine stack. Each cell:

- Owns its own compute, database, message broker partition, and cache.
- Serves a deterministic subset of the workload (e.g., a set of instrument
  symbols, a geographic region, or a customer cohort).
- Is operationally independent: a cell can be upgraded, rolled back, or
  drained without affecting other cells.

```
            ┌──────────── Cell Router ────────────┐
            │  (routes by instrument / tenant)     │
            └──────┬──────────┬──────────┬────────┘
                   ▼          ▼          ▼
             ┌─────────┐ ┌─────────┐ ┌─────────┐
             │ Cell A   │ │ Cell B   │ │ Cell C   │
             │ AAPL,MSFT│ │ GOOG,META│ │ TSLA,NVDA│
             │ Engine   │ │ Engine   │ │ Engine   │
             │ DB       │ │ DB       │ │ DB       │
             │ Broker   │ │ Broker   │ │ Broker   │
             └─────────┘ └─────────┘ └─────────┘
```

---

## 3. Cell Routing

### 3.1 Affinity Key

The **cell affinity key** determines which cell handles a given request.
Common strategies:

| Strategy | Key | Trade-off |
|----------|-----|-----------|
| Instrument-based | Instrument symbol hash | Even distribution for diversified flow; skewed if one instrument dominates. |
| Tenant-based | Client/account ID hash | Isolates noisy tenants; harder to rebalance. |
| Geographic | Datacenter region | Latency-optimal; requires cross-region reconciliation for global instruments. |

### 3.2 Router Requirements

- Stateless: routing table is configuration-driven, loaded from a control
  plane.
- Fast: routing decision must add < 1ms overhead.
- Observable: emit metrics per cell (request rate, error rate, latency
  percentile).

---

## 4. Blast-Radius Containment

| Failure Type | Containment |
|-------------|------------|
| Bad deployment | Canary to a single cell first; promote only on green health checks. |
| DB corruption / migration failure | Only the affected cell's database is impacted. |
| Runaway query / memory leak | Cell's resource limits (CPU, memory) prevent cascade. |
| Broker partition lag | Only the affected cell's event consumers stall. |

---

## 5. Cross-Cell Concerns

Some operations span cells (e.g., portfolio-level risk calculations,
cross-instrument spread orders):

- Use a **global read model** that aggregates events from all cells
  (eventually consistent).
- Cross-cell commands are routed through a **coordination service** that
  orchestrates via Sagas (see `saga-distributed-transactions.md` in the
  banking preset for the Saga pattern; the same principle applies here).
- Never allow direct cell-to-cell communication.

---

## 6. Capacity Planning

- Size cells so that each operates at ≤ 60% peak capacity under normal
  conditions, leaving headroom for failover absorption.
- When a cell is drained (maintenance), its workload is redistributed to
  remaining cells via the router's rebalance mechanism.
- Autoscaling adds new cells (not bigger cells) — horizontal only.

---

## 7. Integration with Spec-Kit Workflow

| Phase | Cell-Based Activity |
|-------|---------------------|
| `/speckit.specify` | Define cell affinity key and workload partitioning strategy. |
| `/speckit.plan` | Size cells, define SLOs per cell, plan canary deployment pipeline. Reference this pattern in the System Design Plan. State which DDD Aggregates are cell-scoped. |
| `/speckit.tasks` | Separate: cell router, cell template (IaC), health-check probes, global read-model aggregator. |
| `/speckit.implement` | Deploy with a single cell first; add cells incrementally; chaos-test cell isolation. |

---

## References

- AWS, *Cell-Based Architecture* (Well-Architected Labs).
- See also: `cqrs-order-sequencing.md`, `event-driven-microservices.md`.
