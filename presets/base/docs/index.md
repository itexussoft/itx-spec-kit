# Itexus Knowledge Base

Use this index for progressive loading during implementation.

Start from `.specify/context/execution-brief.md` when available. It is the compact agent-facing summary for objective, scope, active risks, verification targets, and next actions.

- `workflow-and-gates.md`: Tiered gate behavior and delivery flow
- `migration-guide.md`: Incremental adoption path and legacy-to-current mapping for existing users
- `domain-selection.md`: How domain overlays influence constraints
- `delivery-mechanics.md`: Branching, commits, PR policy, and review feedback loop

## Governance Artifacts

- `decision-authority.yml`: Decision authority matrix for autonomous/propose/human outcomes
- `input-contracts.yml`: Required/optional inputs and validation rules per workflow phase
- `notification-events.yml`: Event contract for lifecycle, gate, approval, and error notifications
- `workflow-state-schema.yml`: Persisted workflow-state structure for resumable execution

Raw gate feedback and pre-action audit log entries remain control-plane artifacts.
Open them directly only when investigating gate behavior or when a human asks.

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
- `asynchronous-event-loop-architecture.md`: Single-process asyncio daemons for concurrent I/O integration (log watch, chat, HTTP sidecars)

Domain-specific patterns are layered on top during initialization based on the selected domain.

## Anti-Patterns

- `over-engineered-cli.md`: Avoid applying heavyweight DDD/Hexagonal architecture to tool-class projects where explicit orchestration is sufficient

## Templates

- `spec-template.md`: Feature specification template
- `architecture-decision-record-template.md`: Standard ADR format
- `system-design-plan-template.md`: Mandatory template for the `/speckit.plan` phase
- `patch-plan-template.md`: Lightweight plan template for scoped patch-level changes
- `refactor-plan-template.md`: Refactor-focused plan template for behavior-preserving structural changes
- `bugfix-report-template.md`: Bugfix-focused report template for defect reproduction, root cause, and fix strategy
- `migration-plan-template.md`: Migration-focused plan template for phased transitions
- `spike-note-template.md`: Exploratory note template for short investigation spikes
- `modify-plan-template.md`: Behavior-change plan template for scoped modifications
- `hotfix-report-template.md`: Incident-linked template for urgent production fixes
- `deprecate-plan-template.md`: Deprecation plan template with dependency-impact tracking
- `execution-brief-template.md`: Compact agent-facing execution summary format
- `test-strategy-template.md`: Standalone test strategy template for implementation planning
- `qa-checklist-template.md`: QA checklist for implementation review and handoff
- `done-report-template.md`: Delivery completion report for traceability and merge handoff
