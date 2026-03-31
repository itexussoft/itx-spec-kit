# Itexus Knowledge Base

Use this index for progressive loading during implementation.

- `workflow-and-gates.md`: Tiered gate behavior and delivery flow
- `domain-selection.md`: How domain overlays influence constraints

## Foundational Principles

- `foundational-principles.md`: SoC, KISS, YAGNI, DRY (Rule of Three), SOLID — universal guardrails enforced during Analyze and Plan phases

## Architectural Patterns

Base patterns (available in `.specify/patterns/` after initialization):

- `domain-driven-design.md`: Bounded Contexts, Aggregates, Entities, Value Objects
- `hexagonal-architecture.md`: Ports and Adapters implementation guidelines
- `clean-architecture.md`: Dependency rule and use-case driven design
- `modular-monolith.md`: Module isolation and cross-module communication via events
- `event-driven-microservices.md`: Eventual consistency and async communication
- `transactional-outbox.md`: Reliable messaging to prevent dual-write data loss
- `e2e-testing-strategy.md`: E2E testing rules for journey coverage, infrastructure, isolation, and assertions

Domain-specific patterns are layered on top during initialization based on the selected domain.

## Templates

- `spec-template.md`: Feature specification template
- `architecture-decision-record-template.md`: Standard ADR format
- `system-design-plan-template.md`: Mandatory template for the `/speckit.plan` phase
- `patch-plan-template.md`: Lightweight plan template for scoped patch-level changes
- `test-strategy-template.md`: Standalone test strategy template for implementation planning
- `qa-checklist-template.md`: QA checklist for implementation review and handoff
