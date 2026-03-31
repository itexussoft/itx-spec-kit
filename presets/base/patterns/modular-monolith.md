# Modular Monolith

> **Applicability:** Projects that need strong module boundaries without the
> operational overhead of distributed microservices. This is the recommended
> **default deployment topology** for new projects in itexus-spec-kit.

---

## 1. What Is a Modular Monolith?

A single deployable unit composed of well-isolated modules, where each
module maps 1:1 to a DDD Bounded Context. Modules communicate through
explicit public APIs and asynchronous events — never through shared mutable
state or direct database access across module boundaries.

---

## 2. Module Isolation Rules

| Rule | Enforcement |
|------|------------|
| Each module owns its database schema (logical separation at minimum, physical separation preferred). | Migration scripts are scoped per module; no cross-module foreign keys. |
| Modules expose a **public API** (a thin facade or service interface) and hide all internals. | Module-internal packages/namespaces are not exported. |
| No module may import another module's domain model. | Static analysis / import-linter rules; gate validators can verify. |
| Shared kernel between modules is explicit, versioned, and minimal. | Extract to a `shared-kernel` library only for true cross-cutting types (e.g., `Money`, `UserId`). |

---

## 3. Cross-Module Communication

### 3.1 Synchronous (In-Process)

A module may call another module's **public facade** synchronously when
immediate consistency is required.

- Calls go through an interface; the calling module must not depend on the
  target module's internals.
- Use sparingly — synchronous coupling is the gateway to a distributed
  monolith when extracting to microservices later.

### 3.2 Asynchronous (In-Process Event Bus)

The preferred communication mechanism. A lightweight in-process event bus
routes domain events from the publishing module to subscribing modules.

- Events are defined in the publishing module's public API.
- Subscribers react in their own transaction scope (eventual consistency).
- The event bus implementation is infrastructure — replaceable with Kafka,
  RabbitMQ, or SQS when a module is extracted to its own service.

```
┌─────────────┐    DomainEvent    ┌─────────────┐
│  Order       │ ───────────────► │  Inventory   │
│  Module      │  (in-process     │  Module      │
│              │   event bus)     │              │
└─────────────┘                   └─────────────┘
```

---

## 4. Module Internal Structure

Each module follows `hexagonal-architecture.md` internally:

```
modules/
├── order/
│   ├── domain/
│   ├── application/
│   ├── adapter/
│   ├── api/              # Public facade interfaces and DTOs
│   └── config/
├── inventory/
│   ├── domain/
│   ├── application/
│   ├── adapter/
│   ├── api/
│   └── config/
└── shared-kernel/        # Minimal cross-cutting types
    ├── money.py
    └── user_id.py
```

---

## 5. Extracting to Microservices

A well-built modular monolith makes future extraction trivial:

1. Replace the in-process event bus with a message broker adapter.
2. Replace synchronous facade calls with gRPC / REST clients.
3. Split the database schema into separate databases.
4. Deploy the extracted module independently.

The module's internal Hexagonal structure remains unchanged.

---

## 6. When to Prefer Microservices From Day One

- Independent scaling requirements per module (e.g., trading engine vs.
  back-office reporting).
- Separate team ownership with decoupled release cycles.
- Regulatory isolation requirements (e.g., PCI-scoped payment module).

In these cases, apply `event-driven-microservices.md` directly.

---

## 7. Integration with Spec-Kit Workflow

| Phase | Modular Monolith Activity |
|-------|--------------------------|
| `/speckit.plan` | Identify modules (= Bounded Contexts). Define public API surface per module. State event contracts. Reference this pattern in the System Design Plan. |
| `/speckit.tasks` | Tasks are scoped to a single module. Cross-module tasks are split: publisher side + subscriber side. |
| `/speckit.analyze` | Verify no cross-module import leakage. Verify event schema compatibility. |
| `/speckit.implement` | Build modules inside-out; wire the event bus last. |

---

## References

- Kamil Grzybek, *Modular Monolith: A Primer* (2019).
- See also: `domain-driven-design.md`, `hexagonal-architecture.md`,
  `event-driven-microservices.md`.
