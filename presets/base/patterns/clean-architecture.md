# Clean Architecture

> **Applicability:** Every project bootstrapped by itexus-spec-kit.
> Complements Hexagonal Architecture with an explicit **Dependency Rule**
> and use-case-centric design. Both patterns are compatible and
> often used together.

---

## 1. The Dependency Rule

Source-code dependencies must point **inward** — toward higher-level
policies and away from implementation details.

```
  Outermost              Innermost
  ──────────────────────────────────►
  Frameworks   Adapters   Use Cases   Domain (Entities)
  & Drivers    (Interface  (Application  (Enterprise
               Adapters)   Business      Business
                           Rules)        Rules)
```

Nothing in an inner circle may reference anything in an outer circle.
Names (classes, functions, variables) declared in an outer circle must not
be mentioned by code in an inner circle.

---

## 2. Layer Responsibilities

### 2.1 Entities (Domain Layer)

Enterprise-wide business rules encapsulated in Aggregates, Entities, Value
Objects, and Domain Events (see `domain-driven-design.md`).

- No framework imports.
- No I/O.
- Pure business logic and invariant enforcement.

### 2.2 Use Cases (Application Layer)

Application-specific business rules that orchestrate domain objects to
fulfill a user's intent.

- Each Use Case class has a single `execute` / `handle` method.
- Accepts a **Request Model** (input DTO), returns a **Response Model**
  (output DTO).
- Calls Repository and Gateway **interfaces** — never concrete
  implementations.
- Must not contain domain business rules; delegate to Aggregates.

### 2.3 Interface Adapters

Converters that translate data between the format most convenient for
Use Cases / Entities and the format most convenient for external agents
(web, database, external service).

- **Controllers / Presenters**: convert HTTP/gRPC requests into Use Case
  Request Models and Use Case Response Models into HTTP/gRPC responses.
- **Repository Implementations**: convert domain objects to/from database
  rows.
- **Gateway Implementations**: translate domain calls into external API
  calls.

### 2.4 Frameworks & Drivers

The outermost ring: web server bootstrap, ORM configuration, message broker
client libraries, container orchestration. Code here is glue — minimal
custom logic.

---

## 3. Crossing Boundaries

When an outer layer must communicate inward, it does so through a
**Boundary Interface** owned by the inner layer. The outer layer provides
the implementation (Dependency Inversion Principle).

When an inner layer must call outward (e.g., save to DB), it calls a
**Port** interface defined in its own layer. The outer layer supplies the
**Adapter**.

Data that crosses a boundary must be a simple DTO — never a database row
object or an ORM entity.

---

## 4. Relationship to Hexagonal Architecture

| Concept | Clean Architecture | Hexagonal |
|---------|-------------------|-----------|
| Inbound entry | Controller + Use Case | Driving Adapter + Driving Port |
| Outbound exit | Use Case → Port → Adapter | Application → Driven Port → Driven Adapter |
| Central model | Entities | Domain Model |
| Dependency direction | Always inward | Always toward center |

Both models agree: the domain is dependency-free. Use whichever vocabulary
the team prefers; this kit treats them as synonyms with the module layout
from `hexagonal-architecture.md`.

---

## 5. Enforcement During Implementation

| Technique | Detail |
|-----------|--------|
| Static import analysis | Gate validators or linter rules ensure no inner-layer module imports from an outer layer. |
| ArchUnit / import-linter | Language-specific tools (Java ArchUnit, Python import-linter) encode the dependency rule as executable tests. |
| Code review checklist | The `architecture-decision-record-template.md` should reference which layers a change touches. |

---

## 6. Integration with Spec-Kit Workflow

| Phase | Clean Architecture Activity |
|-------|-----------------------------|
| `/speckit.plan` | Map every feature to one or more Use Cases. State the layers involved. Reference this pattern by name in the System Design Plan. |
| `/speckit.tasks` | One task per Use Case; separate tasks for adapter wiring. |
| `/speckit.analyze` | Verify no dependency-rule violations in the proposed task breakdown. |
| `/speckit.implement` | Build inside-out: domain first, use cases second, adapters last. |

---

## References

- Robert C. Martin, *Clean Architecture* (2017).
- See also: `hexagonal-architecture.md`, `domain-driven-design.md`.
