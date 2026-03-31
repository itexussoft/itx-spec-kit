# Anti-Pattern: Blocking I/O on Hot Paths

> **Domain:** Fintech — Trading
> **Severity:** MUST NOT — causes latency spikes that violate SLA and risk regulatory penalties.
> **Remedy:** Asynchronous I/O, non-blocking data structures, off-thread side effects.

---

## 1. Definition

A **hot path** is any code executed on every order, quote, or market-data tick
in the critical latency pipeline. **Blocking I/O** on a hot path means the
thread waits synchronously for a network call, disk write, or lock acquisition,
stalling the entire pipeline.

---

## 2. Why It Is Harmful in Trading

| Problem | Consequence |
|---------|-------------|
| **Latency spike.** | A single 50ms database call on the order path turns a 2ms operation into 52ms — a 26x regression. |
| **Thread starvation.** | Blocking threads under load exhausts the thread pool; subsequent orders queue behind I/O waits. |
| **Tail latency.** | P99/P999 latencies balloon, triggering exchange timeouts and missed fills. |
| **Regulatory risk.** | Best-execution obligations (MiFID II, SEC Rule 606) require demonstrable low-latency order routing. |
| **Cascading failure.** | A slow downstream service (risk engine, market data feed) propagates back-pressure to the entire order pipeline. |

---

## 3. Common Violations

| Violation | Where It Appears |
|-----------|-----------------|
| Synchronous database write inside order validation. | Risk check handler. |
| HTTP call to external pricing service on the fill path. | Fill processor. |
| File-system audit log write on every tick. | Market data ingestion. |
| Acquiring a global mutex to update a shared position map. | Position service. |
| Synchronous logging to a remote aggregator. | Anywhere on the order path. |

---

## 4. Compliant Alternatives

| Blocking Operation | Non-Blocking Replacement |
|-------------------|--------------------------|
| Synchronous DB write | Append to an in-memory write-ahead buffer; flush asynchronously. |
| HTTP call to external service | Pre-cache the response; refresh on a background timer. |
| File-system audit log | Write to a lock-free ring buffer; drain to disk on a dedicated I/O thread. |
| Global mutex for position map | Use a lock-free concurrent data structure or actor-per-instrument. |
| Synchronous remote logging | Fire-and-forget to an async log sink (structured logging library). |

### Architecture Sketch

```
Order arrives
  → [Lock-free queue] → Validation (CPU-only, no I/O)
                        → [Lock-free queue] → Exchange Gateway (async TCP)
                                              → [Ring buffer] → Audit Writer (dedicated I/O thread)
```

---

## 5. Measurement Requirement

Every hot-path handler must record:

- **P50, P95, P99, P999 latencies** (histogram metric).
- **I/O wait time** as a separate metric (must be < 1% of total handler time).
- **Thread pool utilization** (alert if > 80% of threads are blocked).

Include these metrics as acceptance criteria in the spec template.

---

## 6. AI Agent Directives

1. **NEVER** place a synchronous I/O call (database, HTTP, file, socket) on any
   code path that executes per-order or per-tick.
2. **ALWAYS** use asynchronous, non-blocking I/O for exchange communication,
   persistence, and logging on hot paths.
3. Prefer lock-free data structures (ring buffers, concurrent queues) over
   mutexes for shared state on the critical path.
4. Side effects (audit logging, analytics) must be decoupled from the hot path
   via async buffers or background threads.
5. Include latency histogram metrics (P50/P95/P99) as mandatory acceptance
   criteria in the feature spec.
6. During code review, flag any `await` / `.Result` / `.Wait()` / `sleep` /
   `synchronized` block that appears inside an order-processing function.
