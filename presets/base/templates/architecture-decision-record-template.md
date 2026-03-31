# ADR-NNNN: [Short Title of Decision]

> **Status:** [Proposed | Accepted | Deprecated | Superseded by ADR-XXXX]
> **Date:** YYYY-MM-DD
> **Deciders:** [List people or roles involved]

---

## Context

_What is the issue that motivates this decision? What forces are at play?
Include relevant technical, business, and regulatory constraints._

## Decision

_What is the change that we're proposing and/or doing?
State the decision in full sentences: "We will use X for Y because Z."_

### Patterns Applied

_List the architectural patterns from `.specify/patterns/` that this
decision relies on. For each, state which DDD Aggregates are involved._

| Pattern | File Reference | Aggregates / Bounded Contexts |
|---------|---------------|-------------------------------|
| _e.g., Hexagonal Architecture_ | `hexagonal-architecture.md` | _e.g., Order, Inventory_ |
| _e.g., Transactional Outbox_ | `transactional-outbox.md` | _e.g., Order (outbox publisher)_ |

## Consequences

### Positive

- _What becomes easier?_

### Negative

- _What becomes harder or more expensive?_

### Risks

- _What could go wrong? What is the mitigation?_

## Alternatives Considered

| Alternative | Reason for Rejection |
|------------|---------------------|
| _Option A_ | _Why it was not chosen_ |
| _Option B_ | _Why it was not chosen_ |

## Compliance Notes

_If this decision has regulatory implications (PSD2, HIPAA, PCI-DSS, etc.),
state them here._

---

_Template source: `presets/base/templates/architecture-decision-record-template.md`_
