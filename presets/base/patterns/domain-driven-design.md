# Domain-Driven Design (DDD) — Foundational Guidelines

> **Applicability:** Every project bootstrapped by itexus-spec-kit.
> This pattern is the strategic backbone; all other patterns in this kit
> assume the vocabulary and structure defined here.

---

## 1. Strategic Design

### 1.1 Bounded Contexts

A Bounded Context is the explicit boundary within which a particular domain
model applies. Each context owns its own Ubiquitous Language, persistence,
and deployment artifact.

**Rules for the AI agent during the Plan phase:**

- Identify every Bounded Context the feature touches.
- Draw a Context Map showing relationships (Shared Kernel, Customer–Supplier,
  Conformist, Anti-Corruption Layer, Open Host Service, Published Language).
- Never let one context directly reference another context's internal entities.
  Use integration events or an ACL adapter instead.

### 1.2 Ubiquitous Language

Every Bounded Context maintains a glossary. Terms that collide across
contexts (e.g., "Account" in banking vs. trading) must be disambiguated
with context-qualified names in code and documentation.

---

## 2. Tactical Building Blocks

### 2.1 Aggregates

An Aggregate is a cluster of domain objects treated as a single unit for
data changes. The **Aggregate Root** is the only entry point for mutations.

| Guideline | Rationale |
|-----------|-----------|
| Keep Aggregates small — prefer single-entity roots. | Reduces contention and simplifies concurrency. |
| Reference other Aggregates by identity (ID), not object reference. | Prevents cross-aggregate coupling and allows separate scaling. |
| Enforce all invariants inside the Aggregate boundary. | The Aggregate is the consistency boundary. |
| Emit domain events from the Aggregate Root after state changes. | Enables downstream reactions without bidirectional coupling. |
| Apply optimistic concurrency (version field) on every Aggregate Root. | Protects against lost updates in concurrent scenarios. |

### 2.2 Entities

Objects with a unique identity that persists across state transitions.

- The identity must be immutable once assigned.
- Equality is based on identity, not attribute values.
- Entities live inside an Aggregate; only the Root is directly loadable
  from the repository.

### 2.3 Value Objects

Immutable objects defined entirely by their attributes, with no conceptual
identity.

- Override equality to compare all attributes.
- Prefer Value Objects for monetary amounts, date ranges, addresses,
  coordinates, measurement units.
- Never give a Value Object its own database table unless it is a large
  collection inside an Aggregate (then use a joined child table).

### 2.4 Domain Events

A record of something that happened in the domain, expressed in past tense
using Ubiquitous Language (e.g., `OrderPlaced`, `AccountCredited`).

- Events are immutable once published.
- Include the Aggregate ID, a monotonically increasing event version, and
  a UTC timestamp.
- Events crossing Bounded Context boundaries must go through a Published
  Language (shared schema / protobuf / Avro).

### 2.5 Domain Services

Stateless operations that don't naturally belong to a single Entity or Value
Object. Use sparingly — prefer placing logic in the Aggregate first.

### 2.6 Repositories

Abstract the persistence mechanism for an Aggregate Root.

- One Repository per Aggregate Root.
- The interface lives in the domain layer; the implementation lives in the
  infrastructure layer (see `hexagonal-architecture.md`).
- Repository methods must return fully reconstituted Aggregate graphs, never
  partial projections (use a Read Model for queries).

---

## 3. Applying DDD in the Spec-Kit Workflow

| Workflow Phase | DDD Activity |
|----------------|-------------|
| `/speckit.specify` | Identify Bounded Contexts; draft Context Map; define Ubiquitous Language terms in `glossary.md`. |
| `/speckit.plan` | Select Aggregates, Entities, Value Objects; reference this pattern by name in the System Design Plan. |
| `/speckit.tasks` | Each task should operate within a single Aggregate to keep PRs focused. |
| `/speckit.analyze` | Verify no cross-aggregate write coupling; verify event schemas are backward-compatible. |
| `/speckit.implement` | Enforce repository-per-aggregate; ensure domain events are emitted before persistence commits (see `transactional-outbox.md`). |

---

## 4. Anti-Patterns to Reject

| Anti-Pattern | Why It's Harmful |
|-------------|-----------------|
| Anemic Domain Model | Business rules leak into services; Aggregates become data bags. |
| God Aggregate | Large aggregates serialize all writes; high contention under load. |
| Cross-Aggregate Transactions | Distributed locks are fragile; prefer eventual consistency with Sagas. |
| Shared Database across Contexts | Tight coupling at the schema level destroys context autonomy. |

---

## References

- Eric Evans, *Domain-Driven Design: Tackling Complexity in the Heart of Software* (2003).
- Vaughn Vernon, *Implementing Domain-Driven Design* (2013).
- See also: `hexagonal-architecture.md`, `clean-architecture.md`, `event-driven-microservices.md`.
