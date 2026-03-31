# Foundational Software Engineering Principles

> **Applicability:** Every project bootstrapped by itexus-spec-kit.
> These principles are the universal guardrails that override stylistic
> preferences and apply regardless of domain, language, or architecture.

---

## 1. Separation of Concerns (SoC)

Each module, class, or function must own exactly one axis of change.
Clear boundaries keep code navigable by both humans and AI agents.

**Rules for the AI agent:**

- Split code along behavioral boundaries, not technical layers alone.
  A feature folder that groups handler + domain + adapter is preferred over
  a flat `controllers/`, `services/`, `repositories/` split when the codebase
  reaches moderate complexity.
- No single file should exceed ~300–400 lines. If it does, it likely
  violates SoC and will degrade AI context-window efficiency.
- Never create "God Classes" that accumulate unrelated responsibilities.
  When a class begins accepting injected dependencies from multiple
  Bounded Contexts, it is a sign that SoC is violated.

---

## 2. KISS (Keep It Simple, Stupid)

Simplicity is the primary defense against accidental complexity.
A correct, readable 20-line function is superior to an "elegant" 5-line
chain that requires three mental stack frames to trace.

**Rules for the AI agent:**

- Before proposing an abstraction, ask: "Can the next developer (or AI
  agent) understand this without reading another file?" If not, simplify.
- Prefer flat control flow. Deeply nested conditionals, callback chains,
  and multi-level generic type parameters are complexity signals.
- When choosing between a well-known stdlib solution and a third-party
  library, prefer stdlib unless the library provides a measurable,
  documented advantage.
- During `/speckit.plan`, if a proposed design introduces more than two
  new abstractions (interfaces, base classes, generic wrappers) for a
  single feature, flag it for simplification.

---

## 3. YAGNI (You Aren't Gonna Need It)

Build exactly what the current spec requires. Speculative generality is
a cost paid now for a benefit that may never arrive.

**Rules for the AI agent:**

- Do not add extension points, plugin systems, or configuration knobs
  unless the spec explicitly demands them.
- Do not pre-build support for databases, message brokers, or cloud
  providers that are not in the current infrastructure requirements.
- If a pattern from `.specify/design-patterns/` is not selected in the
  plan's Section 4b, do not implement it "just in case."
- During `/speckit.analyze`, any task that exists solely to "prepare for
  future work" must be challenged and removed unless backed by a concrete
  spec requirement.

---

## 4. DRY (Don't Repeat Yourself) — with the Rule of Three

Premature DRY creates coupling that is harder to undo than mild
duplication. Extract shared logic only when a pattern has been confirmed.

**Rules for the AI agent:**

- **First occurrence:** Write the code inline.
- **Second occurrence:** Note the duplication in a code comment or task
  tracker, but do not extract yet.
- **Third occurrence:** Extract into a shared function, module, or base
  abstraction. At this point the pattern is confirmed and the right
  abstraction boundary is visible.
- Never create a base class solely because two classes share a method.
  Prefer composition (shared collaborator object) over inheritance.
- When extracting, ensure the shared code lives at the correct layer.
  Domain logic shared across Bounded Contexts should go into a Shared
  Kernel; infrastructure utilities go into a common infrastructure module.

---

## 5. SOLID Principles

### 5.1 Single Responsibility Principle (SRP)

A class/module should have one, and only one, reason to change.
SRP directly impacts AI context-window efficiency: a focused module
can be understood in isolation.

### 5.2 Open/Closed Principle (OCP)

Modules should be open for extension but closed for modification.
Prefer strategy injection and decorator composition over editing
existing classes to add behavior.

### 5.3 Liskov Substitution Principle (LSP)

Subtypes must be substitutable for their base types without altering
program correctness. Avoid "refused bequest" where a subclass overrides
a method to throw `NotImplementedError`.

### 5.4 Interface Segregation Principle (ISP)

No client should be forced to depend on methods it does not use.
Prefer narrow, role-specific interfaces over wide "do everything" ones.

### 5.5 Dependency Inversion Principle (DIP)

High-level modules must not depend on low-level modules; both should
depend on abstractions. This ensures components can be isolated,
tested, and replaced independently.

**Rules for the AI agent:**

- Every adapter (database, HTTP client, message broker) must sit behind
  a port/interface owned by the domain layer.
- Constructor injection is the default DI mechanism. Avoid service
  locator or ambient context patterns.
- In test code, every external dependency must be replaceable with a
  test double via the injected interface.

---

## Enforcement Checkpoint

During the **Analyze** and **Plan** workflow phases, the AI agent must
evaluate its proposed architecture against all five principles above.

| Principle | Gate question |
|-----------|--------------|
| SoC | Does every module have a single axis of change? |
| KISS | Can the design be explained in one paragraph without referencing more than two abstractions? |
| YAGNI | Does every component trace back to a concrete spec requirement? |
| DRY | Are extractions backed by at least three occurrences? |
| SOLID | Are all external dependencies behind injectable interfaces? |

Any **No** answer requires the plan to be revised before proceeding to
the Tasks phase.
