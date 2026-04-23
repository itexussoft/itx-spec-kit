---
tags:
  - event
  - messaging
  - broker
  - consumer
  - producer
  - topic
  - queue
  - command
anti_tags:
  - react
  - ui
  - frontend
  - component
  - click
  - browser
  - dom
  - css
  - html
  - toast
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Event-Driven Microservices

> **Applicability:** Projects requiring independent deployment, scaling, and
> team ownership per Bounded Context. Use when the Modular Monolith
> (see `modular-monolith.md`) no longer satisfies scaling or organizational
> constraints.

---

## 1. Core Tenets

1. **Each microservice = one Bounded Context** with its own data store.
2. **Asynchronous messaging is the default** integration mechanism.
3. **Eventual consistency** is accepted across service boundaries;
   strong consistency is enforced only within a single Aggregate.
4. **Smart endpoints, dumb pipes** — business logic lives in the service,
   not in the messaging infrastructure.

---

## 2. Event Categories

| Category | Description | Example |
|----------|-------------|---------|
| **Domain Event** | Something that happened inside a Bounded Context. | `OrderPlaced`, `AccountCredited` |
| **Integration Event** | A domain event projected into a Published Language schema shared between contexts. | `order.v1.OrderPlaced` (Avro/Protobuf) |
| **Command** | A directed request from one service to another. | `ProcessPayment` |

- Domain Events are internal; Integration Events cross service boundaries.
- Prefer events over commands for loose coupling.

---

## 3. Messaging Infrastructure

### 3.1 Broker Selection

| Broker | Best For |
|--------|---------|
| Apache Kafka | High-throughput, ordered event logs, replay capability. |
| RabbitMQ | Flexible routing, low-latency task queues. |
| AWS SQS + SNS | Managed, serverless-friendly fan-out. |

### 3.2 Topic / Queue Design

- One topic per Integration Event type (e.g., `order.events.v1`).
- Consumer groups per subscribing service for independent offset tracking.
- Dead-letter queues (DLQ) for poison messages with alerting.

---

## 4. Reliable Event Publishing

Use the **Transactional Outbox** pattern (see `transactional-outbox.md`)
to guarantee that events are published if and only if the originating
database transaction commits. Never publish directly to the broker inside
a DB transaction.

---

## 5. Idempotent Consumers

Every consumer must be idempotent because at-least-once delivery is the
norm.

- Store a `processed_event_id` set per consumer.
- Design handlers so that re-processing the same event produces the same
  outcome.

---

## 6. Schema Evolution

- Use a Schema Registry (Confluent, AWS Glue) with backward-compatible
  Avro or Protobuf schemas.
- Additive-only changes (new optional fields) are safe.
- Removing or renaming fields requires a versioned topic migration.

---

## 7. Observability

| Concern | Implementation |
|---------|---------------|
| Distributed tracing | Propagate `trace-id` / `correlation-id` in event headers. |
| Consumer lag monitoring | Alert when lag exceeds SLO thresholds. |
| Event lineage | Maintain an event catalog documenting every Integration Event, its producer, and consumers. |

---

## 8. Failure Modes and Mitigations

| Failure | Mitigation |
|---------|-----------|
| Broker unavailable | Transactional Outbox buffers events in the local DB; relay retries on recovery. |
| Consumer crash | Consumer group rebalances; offset is committed only after successful processing. |
| Poison message | Route to DLQ after N retries; alert on-call. |
| Schema mismatch | Schema Registry rejects incompatible schemas before deployment. |

---

## 9. Integration with Spec-Kit Workflow

| Phase | Event-Driven Activity |
|-------|-----------------------|
| `/speckit.specify` | Identify Integration Events in the Context Map. |
| `/speckit.plan` | Define event schemas, topic structure, and consumer SLOs. Reference this pattern and `transactional-outbox.md` in the System Design Plan. |
| `/speckit.tasks` | Separate tasks: event schema definition, producer implementation, consumer implementation. |
| `/speckit.implement` | Implement Outbox + relay first; then producers; then consumers. |

---

## References

- Chris Richardson, *Microservices Patterns* (2018).
- See also: `transactional-outbox.md`, `domain-driven-design.md`,
  `modular-monolith.md`.
