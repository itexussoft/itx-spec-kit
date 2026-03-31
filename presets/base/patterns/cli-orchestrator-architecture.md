# CLI Orchestrator Architecture (AI-First)

> **Applicability:** CLI tools, automation scripts, workflow engines, and
> integration orchestrators.
> Use this pattern when the project has no domain persistence model and mainly
> coordinates external processes, files, and APIs.

---

## 1. Intent

Build automation tools that are easy for both humans and AI agents to evolve.
Optimize for readability, resumability, and explicit behavior over enterprise
layering.

This pattern intentionally favors small modules, file-based state, and
subprocess boundaries over DDD tactical constructs.

---

## 2. AI-First Architecture Principles

### 2.1 Context-Window Friendly Modules

- Keep files below ~300 lines where possible.
- Split by single concern (`workflow.py`, `state.py`, `events.py`) instead of
  broad technical layers.
- Avoid cross-file hops to understand core behavior.

### 2.2 Explicit Over Implicit

- Prefer direct wiring in entrypoints over magic registries.
- Avoid reflection, metaclasses, hidden side effects, and dynamic imports unless
  strictly required.
- Keep control flow obvious and debuggable from logs.

### 2.3 Flat Over Deep

- Target max two directory levels for core modules.
- Keep call depth shallow from CLI entry to real action.
- Use plain functions and small dataclasses before introducing inheritance.

### 2.4 Stateful by Files, Not by Memory

- Persist workflow progress in YAML/JSON files.
- A stopped process must be resumable from disk without replaying hidden state.
- State files should be readable without tooling.

### 2.5 Idempotent Operations

- Every phase step should safely re-run after interruption.
- Use checkpoint markers and explicit phase status transitions.
- Prefer additive writes and atomic replacement over in-place mutation.

### 2.6 Schema-Driven Contracts

- Define event payloads and state shape via explicit schemas.
- Validate on read, fail fast with actionable errors.
- Keep schema changes versioned and backward-aware.

### 2.7 Minimal Dependency Footprint

- Prefer stdlib first.
- Add third-party dependencies only when they remove substantial complexity.
- Keep runtime install small to improve reliability in CI and ephemeral agents.

---

## 3. Recommended Module Layout

```
engine/
├── cli.py
├── workflow.py
├── state.py
├── config.py
├── gates.py
├── agents.py
├── decisions.py
├── events.py
├── git_ops.py
└── adapters/
    ├── base.py
    ├── webhook.py
    └── chat_runtime.py
```

### Layout Rules

- One module, one primary responsibility.
- Keep adapter code isolated from workflow state logic.
- Keep CLI parsing separate from business orchestration.
- Keep schema validation near file I/O boundaries.

---

## 4. File-Based State Management

### 4.1 State Shape

Use a single workflow state file (for example
`.specify/context/workflow-state.yml`) containing:

- feature metadata
- current phase
- per-phase status and artifacts
- decisions and approvals
- error and retry history

### 4.2 Write Strategy

- Write to a temporary file first.
- Atomically rename to target path.
- Never partially write the canonical state file.

### 4.3 Concurrency Strategy

- Prefer single-writer ownership per workspace.
- If concurrency is needed, lock explicitly via lockfile and timeout.
- Fail fast when a lock cannot be acquired.

---

## 5. Subprocess Orchestration Pattern

When calling external tools (`git`, `gh`, AI agent CLI, quality gates):

- set explicit timeouts
- capture stdout/stderr
- handle non-zero exit codes with actionable context
- handle tool-not-installed errors (`FileNotFoundError`)
- never assume command availability on host

Use subprocess boundaries as reliability contracts. External command failures
must not corrupt internal state.

---

## 6. Exit-and-Resume Pattern (Async HITL)

For human approvals and interventions:

1. persist latest workflow state
2. emit notification event
3. exit process cleanly
4. resume via explicit command that reloads state

Do not keep long-running daemon loops unless required by constraints.
Exit-and-resume is easier to debug, cheaper to operate, and safer for local
development workflows.

---

## 7. Testing Strategy for CLI Orchestrators

### 7.1 Test the Interface Contract

- invoke CLI commands as subprocesses
- assert exit codes
- assert stdout/stderr diagnostics
- assert produced state/artifact files

### 7.2 Mock at External Boundaries

- mock subprocess calls to external tools
- mock webhook/HTTP sends
- keep workflow logic deterministic

### 7.3 Skip Heavy Infrastructure by Default

Containers and broker/database harnesses are optional for this project type.
Use them only when the tool itself depends on those systems at runtime.

---

## 8. When to Use This Instead of DDD/Hexagonal

Choose this pattern when most of the code is:

- orchestration and control flow
- file/state transitions
- command invocation and retries
- notifications and approvals

Do not force Aggregates, Repositories, or deep port/adapter taxonomies when
there is no domain persistence model to protect.

---

## 9. AI Agent Directives

1. For tool-class projects, prefer this pattern over `domain-driven-design.md`
   and `hexagonal-architecture.md`.
2. Keep each module directly understandable without opening more than two
   additional files.
3. Treat workflow state files as the source of truth; never rely on hidden
   in-memory progress.
4. Design every phase operation to be safe under retries and partial failures.
5. Favor explicit logic and small functions over architectural ceremony.

---

## References

- See also: `foundational-principles.md`, `e2e-testing-strategy.md`.
