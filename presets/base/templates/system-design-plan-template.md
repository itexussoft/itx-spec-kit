# System Design Plan — [Feature / Epic Title]

> **Prepared during:** `/speckit.plan` phase
> **Author:** [AI Agent / Human]
> **Date:** YYYY-MM-DD
> **Status:** [Draft | Approved | Superseded]

---

## 1. Problem Statement

_One paragraph describing the business or user problem._

## 2. Bounded Contexts Involved

_Identify every DDD Bounded Context this feature touches.
Reference `domain-driven-design.md` for definitions._

| Bounded Context | Role in This Feature | Ownership |
|----------------|---------------------|-----------|
| _e.g., Context A_ | _Command side_ | _Team Alpha_ |
| _e.g., Context B_ | _Read side_ | _Team Beta_ |

## 3. Context Map

_Describe the relationships between the Bounded Contexts above.
Use DDD Context Map vocabulary: Shared Kernel, Customer–Supplier,
Conformist, Anti-Corruption Layer, Open Host Service, Published Language._

```
[Context A] ──(Customer–Supplier)──► [Context B]
[Context A] ──(Anti-Corruption Layer)──► [External System]
```

## 4. Architectural Patterns Applied

> **MANDATORY:** Consult `.specify/pattern-index.md` for the available pattern
> catalog. Explicitly list which patterns the design utilizes by referencing
> their filenames. The AI agent must not leave this section empty.
>
> In lazy knowledge mode, declare selections in a structured block so the
> gate can materialize them automatically:
>
> `<!-- selected_patterns: domain-driven-design.md, hexagonal-architecture.md -->`

<!-- selected_patterns: none -->

| Pattern | File Reference | Justification |
|---------|---------------|---------------|
| _e.g., Domain-Driven Design_ | `domain-driven-design.md` | _Strategic backbone_ |
| _e.g., Hexagonal Architecture_ | `hexagonal-architecture.md` | _Structural implementation_ |

## 4b. Code-Level Design Patterns Applied

> **MANDATORY:** Walk through every signal row below. For each signal detected
> in this feature, mark **Yes** and record the rationale. For signals that do
> not apply, mark **No** with a brief reason. The AI agent must not leave any
> row unanswered.
>
> These selections flow directly into the spec template's "Code-Level Design
> Patterns" section and govern the Tasks and Implement phases.
>
> For features that apply 2 or fewer code-level patterns, this matrix may be
> replaced by a short prose section listing the selected patterns and rationale.

| # | Signal Detected in This Feature | Pattern to Apply | File Reference | Applies? | Rationale / Notes |
|---|--------------------------------|-----------------|----------------|----------|-------------------|
| 1 | A domain concept is represented as a raw `string`, `int`, or `float`. | Value Object | `value-object-and-result-monad.md` | _Yes / No_ | |
| 2 | An operation can fail for a **business** reason. | Result Monad | `value-object-and-result-monad.md` | _Yes / No_ | |
| 3 | A conditional chain dispatches on a type or status discriminator with **>2 branches**. | Strategy | `strategy-and-composition.md` | _Yes / No_ | |
| 4 | A write operation is exposed via an API endpoint or message consumer. | Command + Handler | `command-and-handler.md` | _Yes / No_ | |
| 5 | The feature integrates with a 3rd-party API, legacy system, or external service. | Adapter / Anti-Corruption Layer | `adapter-anti-corruption.md` | _Yes / No_ | |
| 6 | A cross-cutting concern must apply to multiple handlers. | Decorator / Middleware | `decorator-middleware.md` | _Yes / No_ | |
| 7 | An entity has **>2 status values** with restricted, auditable transitions. | State Machine | `state-machine-pattern.md` | _Yes / No_ | |
| 8 | A complex immutable object requires **>4 constructor parameters** or cross-field validation. | Builder | `builder-for-immutability.md` | _Yes / No_ | |

### Anti-Patterns to Guard Against

> Mark every anti-pattern that is relevant. If a row is marked **Guard**,
> the implementation must include an explicit mitigation.

| # | Anti-Pattern | File Reference | Guard? | Mitigation Strategy |
|---|-------------|----------------|--------|---------------------|
| 1 | Raw primitives for domain concepts. | `primitive-obsession.md` | _Yes / No_ | |
| 2 | Data-only entities with logic in external services. | `anemic-domain-model.md` | _Yes / No_ | |
| 3 | Manual Singleton implementation. | `manual-singleton.md` | _Yes / No_ | |
| 4 | Deep inheritance (>2 levels) or Template Method. | `template-method-inheritance.md` | _Yes / No_ | |
| 5 | Classic Visitor with double-dispatch. | `visitor-boilerplate.md` | _Yes / No_ | |

> **Domain-specific anti-patterns** — fill in if the domain preset provides them.

## 5. DDD Aggregates

> **MANDATORY:** List every Aggregate involved, its root entity, key
> invariants, and the domain events it emits.

| Aggregate Root | Bounded Context | Key Invariants | Domain Events Emitted |
|---------------|----------------|----------------|----------------------|
| _e.g., MyAggregate_ | _Context A_ | _Invariant description_ | `EventA`, `EventB` |

## 6. Component Diagram

_Provide a high-level component diagram showing Bounded Contexts, their
public APIs, and integration events._

## 7. Data Model Sketch

_For each Aggregate, sketch the key entities, value objects, and their
relationships. This is NOT a database schema — it is the domain model._

## 8. Integration Events

_List all events that cross Bounded Context boundaries._

| Event | Producer | Consumer(s) | Schema Format |
|-------|----------|-------------|---------------|
| | | | |

## 9. Non-Functional Requirements

| Concern | Requirement | Approach |
|---------|------------|---------|
| Latency | | |
| Throughput | | |
| Availability | | |
| Consistency | | |
| Security | | |
| Compliance | | |

## 10. Deployment Topology

_State whether this is a Modular Monolith or Microservices deployment.
Reference `modular-monolith.md` or `event-driven-microservices.md`._

## 11. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| | | | |

## 12. Open Questions

- _List anything unresolved that requires clarification before `/speckit.tasks`._

## 13. Test Strategy

> **MANDATORY for Full Plan features.** Declare test coverage before
> implementation begins. The `after_implement` gate verifies that E2E test
> files matching the declared journeys exist.

### Unit Tests

| Aggregate / Module | Key Scenarios | Coverage Target |
|--------------------|---------------|-----------------|
| _e.g., OrderAggregate_ | _Create, cancel, expire_ | _>90%_ |

### Integration Tests

| Integration Boundary | What Is Verified | Test Double Strategy |
|----------------------|------------------|----------------------|
| _e.g., OrderRepo <> DB_ | _CRUD + optimistic locking_ | _Testcontainers Postgres_ |

### End-to-End Tests

| User Journey / Flow | Entry Point | Exit Assertion | Data Setup |
|---------------------|-------------|----------------|------------|
| _e.g., Place order -> confirm_ | _POST /orders_ | _Status CONFIRMED in DB + OrderConfirmed event published_ | _Seeded fixtures_ |

### Test Environment Requirements

- _e.g., Docker Compose with Postgres + RabbitMQ_
- _e.g., WireMock for payment gateway stub_

---

_Template source: `presets/base/templates/system-design-plan-template.md`_
_The AI agent MUST fill every mandatory section during the `/speckit.plan` phase._
