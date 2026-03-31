# Itexus Knowledge Base

Use this index for progressive loading during implementation.

- `workflow-and-gates.md`: Tiered gate behavior and delivery flow
- `domain-selection.md`: How domain overlays influence constraints
- `delivery-mechanics.md`: Branching, commits, PR policy, and review feedback loop

## Governance Artifacts

- `decision-authority.yml`: Decision authority matrix for autonomous/propose/human outcomes
- `input-contracts.yml`: Required/optional inputs and validation rules per workflow phase
- `notification-events.yml`: Event contract for lifecycle, gate, approval, and error notifications
- `workflow-state-schema.yml`: Persisted workflow-state structure for resumable execution

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
- `cli-orchestrator-architecture.md`: AI-first architecture for CLI tools, workflow engines, and automation scripts

Domain-specific patterns are layered on top during initialization based on the selected domain.

## Anti-Patterns

- `over-engineered-cli.md`: Avoid applying heavyweight DDD/Hexagonal architecture to tool-class projects where explicit orchestration is sufficient

## Templates

- `spec-template.md`: Feature specification template
- `architecture-decision-record-template.md`: Standard ADR format
- `system-design-plan-template.md`: Mandatory template for the `/speckit.plan` phase
- `patch-plan-template.md`: Lightweight plan template for scoped patch-level changes
- `test-strategy-template.md`: Standalone test strategy template for implementation planning
- `qa-checklist-template.md`: QA checklist for implementation review and handoff
- `done-report-template.md`: Delivery completion report for traceability and merge handoff
