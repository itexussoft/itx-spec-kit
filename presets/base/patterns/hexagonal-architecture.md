# Hexagonal Architecture (Ports & Adapters)

> **Applicability:** Every project bootstrapped by itexus-spec-kit.
> Provides the structural implementation strategy for the DDD tactical
> building blocks defined in `domain-driven-design.md`.

---

## 1. Core Principle

The domain model sits at the center. It knows nothing about frameworks,
databases, HTTP, or messaging. External concerns connect through **Ports**
(interfaces owned by the domain) and **Adapters** (implementations that
satisfy those interfaces).

```
          ┌──────────────────────────────────────────┐
          │            Driving Adapters               │
          │  (REST, gRPC, CLI, Message Consumer)      │
          └──────────────┬───────────────────────────┘
                         │  Driving Port (Use Case interface)
                         ▼
          ┌──────────────────────────────────────────┐
          │         Application / Use Cases           │
          │  (Orchestrates domain, no business logic) │
          └──────────────┬───────────────────────────┘
                         │  calls Domain Model
                         ▼
          ┌──────────────────────────────────────────┐
          │            Domain Model                   │
          │  (Aggregates, Entities, Value Objects,    │
          │   Domain Events, Domain Services)         │
          └──────────────┬───────────────────────────┘
                         │  Driven Port (Repository / Gateway interface)
                         ▼
          ┌──────────────────────────────────────────┐
          │            Driven Adapters                │
          │  (PostgreSQL, Kafka, S3, SMTP, gRPC       │
          │   client to another Bounded Context)      │
          └──────────────────────────────────────────┘
```

---

## 2. Port Types

### 2.1 Driving (Primary) Ports

Expose the application's capabilities to the outside world.

- Defined as **Use Case interfaces** (e.g., `PlaceOrderUseCase`,
  `TransferFundsUseCase`).
- Each interface method maps 1:1 to an application operation.
- Input is a plain DTO / command object; output is a result DTO.
  Never return domain entities from a driving port.

### 2.2 Driven (Secondary) Ports

Allow the domain / application layers to reach infrastructure without
depending on it.

- **Repository Ports**: `OrderRepository`, `AccountRepository` — defined in
  the domain layer; implemented by a driven adapter (Postgres, Mongo, etc.).
- **Gateway Ports**: `PaymentGateway`, `NotificationGateway` — for calling
  external services.
- **Event Publisher Port**: `DomainEventPublisher` — for sending domain
  events to a message broker (see `transactional-outbox.md`).

---

## 3. Adapter Implementation Rules

| Rule | Detail |
|------|--------|
| One adapter class per technology concern. | `PostgresOrderRepository`, `KafkaEventPublisher` — never a single "InfraService" dumping ground. |
| Adapters depend on ports, never on each other. | If two adapters need to share logic, extract a common utility, not a cross-adapter call. |
| Adapters are wired via dependency injection. | Constructor injection at composition root. No service locator. |
| Adapters are the only place allowed to import framework-specific packages. | `import sqlalchemy`, `import kafka` — never in domain or use-case layers. |

---

## 4. Package / Module Layout

A suggested layout aligned with DDD + Hexagonal:

```
<bounded-context>/
├── domain/
│   ├── model/              # Aggregates, Entities, Value Objects
│   ├── event/              # Domain Event definitions
│   ├── service/            # Domain Services (stateless)
│   └── port/
│       ├── repository.py   # Repository interfaces
│       └── gateway.py      # External gateway interfaces
├── application/
│   ├── use_case/           # Driving port implementations (orchestrators)
│   ├── dto/                # Input/output DTOs
│   └── port/
│       └── event_publisher.py
├── adapter/
│   ├── inbound/            # REST controllers, gRPC handlers, CLI, consumers
│   └── outbound/           # DB repos, message publishers, HTTP clients
└── config/                 # Wiring / composition root / DI container setup
```

---

## 5. Testing Strategy

| Layer | Test Type | Dependencies |
|-------|-----------|-------------|
| Domain | Unit tests | None — pure logic, no mocks needed. |
| Application (Use Cases) | Unit tests with mocked driven ports | Stub repositories, gateways. |
| Adapters (Inbound) | Integration tests | Real HTTP server or gRPC stub. |
| Adapters (Outbound) | Integration tests | Real DB (testcontainers) or embedded broker. |
| Full Hexagon | End-to-end (E2E) | Docker Compose or equivalent harness. |

---

## 6. Integration with Spec-Kit Workflow

| Phase | Hexagonal Activity |
|-------|-------------------|
| `/speckit.plan` | Declare which ports exist; state adapter technology choices; reference this pattern by name in the System Design Plan. |
| `/speckit.tasks` | Split tasks by layer: domain model tasks, use-case tasks, adapter tasks. |
| `/speckit.implement` | Enforce the dependency rule — imports must flow inward. Gate validators can statically check import directions. |

---

## References

- Alistair Cockburn, *Hexagonal Architecture* (2005).
- See also: `clean-architecture.md`, `domain-driven-design.md`.
