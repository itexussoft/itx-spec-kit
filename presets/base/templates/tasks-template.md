# Tasks — [Feature / Epic Title]

> **Produced by:** `/speckit.tasks`
> **Source spec:** `specs/<feature>/spec.md`
> **Source plan:** `specs/<feature>/system-design-plan.md`, `patch-plan.md`, `refactor-plan.md`, `bugfix-report.md`, `migration-plan.md`, `spike-note.md`, `modify-plan.md`, `hotfix-report.md`, or `deprecate-plan.md`
> **Date:** YYYY-MM-DD

---

## Format Rules

Every task item **MUST** use markdown checkbox syntax:

- `- [ ]` for a pending task
- `- [x]` for a completed task

The AI agent **MUST** update each checkbox from `[ ]` to `[x]` as it
completes the corresponding work during `/speckit.implement`. Do **NOT**
remove or rewrite completed items — only flip the checkbox.

---

## Phase 1 — [Phase Name, e.g. Domain Layer]

- [ ] Task description — acceptance criteria or key detail
- [ ] Task description — acceptance criteria or key detail

## Phase 2 — [Phase Name, e.g. Application Layer]

- [ ] Task description — acceptance criteria or key detail
- [ ] Task description — acceptance criteria or key detail

## Phase 3 — [Phase Name, e.g. Infrastructure / Adapters]

- [ ] Task description — acceptance criteria or key detail

## Phase 4 — [Phase Name, e.g. Testing]

- [ ] Task description — acceptance criteria or key detail
- [ ] Task description — acceptance criteria or key detail

---

_Template source: `presets/base/templates/tasks-template.md`_
_The AI agent MUST use `- [ ]` checkbox syntax for every task. Mark `- [x]` when a task is completed during `/speckit.implement`._
