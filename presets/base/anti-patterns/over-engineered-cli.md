# Over-Engineered CLI Tool

> **Applicability:** CLI tools, automation scripts, workflow engines, and
> orchestration services.
> This anti-pattern appears when enterprise DDD/application architecture is
> mechanically applied to lightweight tool-class software.

---

## 1. Problem

Tool-class projects often coordinate files, subprocesses, and APIs with limited
domain complexity. Applying heavy tactical architecture here adds ceremony,
expands surface area, and harms maintainability for both humans and AI agents.

Symptoms include many abstractions with little behavior, deep file trees, and
high context-switch cost to follow simple execution flows.

---

## 2. Smells and Correctives

### 2.1 DDD Aggregates for File-State Workflows

**Smell:** Introduces Aggregate Roots, Entities, Value Objects, and domain
repositories for a YAML/JSON state file.

**Why harmful:** Large abstraction tax for simple read/write workflows. Hides
real behavior behind boilerplate.

**Do instead:** Use explicit state schema + dataclass/model + atomic file
persistence.

### 2.2 Repository Pattern for Plain Files

**Smell:** `IWorkflowRepository`, `YamlWorkflowRepository`, `CachedRepository`
just to call `yaml.safe_load` and `write_text`.

**Why harmful:** Creates fake boundaries and extra indirection with no
substitutability benefit.

**Do instead:** Keep file I/O in `state.py` with clear load/save functions and
schema validation.

### 2.3 UseCase Class Explosion for CLI Commands

**Smell:** Separate class per command with thin wrappers and little logic.

**Why harmful:** Inflates project size; every change requires touching many
files.

**Do instead:** Use command handlers as focused functions or small callable
objects only when stateful behavior is needed.

### 2.4 DI Framework for Small Tooling Projects

**Smell:** Adds IoC container, providers, and runtime wiring metadata for <15
modules.

**Why harmful:** Reduces readability, introduces hidden wiring failures, and
increases startup/debug complexity.

**Do instead:** Wire dependencies explicitly in `main()` / `cli.py`.

### 2.5 Daemon Runtime for Approval Wait States

**Smell:** Long-running service remains active while waiting for human input.

**Why harmful:** Operationally fragile, harder to recover, and unnecessary for
asynchronous approval workflows.

**Do instead:** Persist state, notify, exit. Resume explicitly on approval.

### 2.6 Event Sourcing for Simple Workflow Status

**Smell:** Stores full append-only event history and replay logic for phase
state that can be represented in one snapshot.

**Why harmful:** Adds replay bugs, schema migration complexity, and debugging
cost.

**Do instead:** Use a canonical workflow snapshot with optional bounded audit
entries.

### 2.7 Abstract Factory for Few Adapters

**Smell:** Multi-layer factory hierarchy to instantiate 2-3 adapters.

**Why harmful:** Obscures control flow and complicates extension points.

**Do instead:** Use a straightforward mapping (`type -> constructor`) and
validate configuration upfront.

---

## 3. Detection Checklist

Flag this anti-pattern when all are true:

- core business logic is mostly orchestration
- project has no rich domain model or persistence invariants
- architecture introduces more abstraction files than behavior files
- a newcomer cannot trace command flow in under 10 minutes

---

## 4. Refactoring Path

1. Flatten module hierarchy and remove empty interfaces.
2. Consolidate trivial wrappers into direct functions.
3. Replace DI container with explicit construction in entrypoint.
4. Replace event replay mechanics with explicit workflow snapshot.
5. Add schema validation and atomic writes for the canonical state file.

---

## 5. AI Agent Directives

1. If the project is a CLI/workflow orchestrator, do not introduce DDD tactical
   layers unless a concrete persistence-rich domain model exists.
2. Reject abstractions that cannot be tied to a current spec requirement.
3. Prefer explicit, testable orchestration flow over architectural ceremony.
4. Keep architecture proportional to problem complexity and operational needs.

---

## References

- See also: `../patterns/cli-orchestrator-architecture.md`,
  `../patterns/foundational-principles.md`.
