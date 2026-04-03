# Workflow and Gates

Delivery stages:

1. Constitution (`/speckit.constitution`)
2. Specify (`/speckit.specify`)
3. Clarify (`/speckit.clarify`, optional)
4. Plan (`/speckit.plan`) — read `.specify/pattern-index.md`, select relevant pattern files, and produce a System Design Plan (`system-design-plan-template.md`) or a patch/tool plan (`patch-plan-template.md`). In lazy knowledge mode, read full candidate pattern content from `.specify/.knowledge-store/` during planning.
5. **`after_plan` gate** — validates plan presence + mandatory sections; in lazy knowledge mode, materializes only selected pattern files into `.specify/`
6. Tasks (`/speckit.tasks`) — produces **`tasks.md`** in the active feature directory using `tasks-template.md` as format reference. Every task **must** use `- [ ]` checkbox syntax.
7. **`after_tasks` gate** — validates tasks file presence and checkbox format
8. Analyze (`/speckit.analyze`, optional) — **only after** `tasks.md` exists; cross-artifact check needs the task inventory
9. Implement (`/speckit.implement`)
10. **`after_implement` gate** — validates E2E test presence and assertion quality, then runs domain-specific validators
11. Test / Cleanup / Review (extensions + gates)
12. **`after_review` gate** — validates delivery readiness (all tasks completed, no outstanding Tier 2 feedback, E2E checks still present)
13. Deliver — prepare done report and open PR for human merge decision

If **`/speckit.analyze` is blocked** with "tasks.md not found", run **`/speckit.tasks`** again (and ensure spec + plan exist for that feature).

## Task format

`tasks.md` must use markdown checkbox syntax for every task item:

```
- [ ] Pending task description
- [x] Completed task description
```

During `/speckit.implement`, the AI agent flips each checkbox from `[ ]` to `[x]` as it finishes the corresponding work. Completed items must **not** be removed or rewritten — only the checkbox state changes. This gives reviewers a clear progress trail.

The `after_tasks` gate checks that at least one tasks file exists in supported locations and emits a Tier 1 warning when a tasks file contains bare list items (`- task`). Use checkbox syntax for all task items (`- [ ]` / `- [x]`).

See `tasks-template.md` for the full template.

## Pattern selection in plans

Plans declare which knowledge files they need using a structured HTML comment block:

```
<!-- selected_patterns: domain-driven-design.md, hexagonal-architecture.md -->
```

Patch plans that do not require patterns should use:

```
<!-- selected_patterns: none -->
```

For backward compatibility, the gate also accepts inline backtick references to `*.md` filenames. The structured block is preferred because it is unambiguous and allows explicit opt-out.

## Gate hooks

Gate enforcement rules (mandatory sections, placeholder markers, retry limits) are defined in `.specify/policy.yml`, which is copied from `presets/base/policy.yml` during initialization.

| Hook | Fires After | Validates |
|------|------------|-----------|
| `after_plan` | `/speckit.plan` | Plan file exists; Full Plan requires Sections 4, 4b, 5, and 13 with real content; Patch Plan and Tool Plan require Sections 1 and 2 with real content. In lazy mode, selected pattern filenames are resolved from the knowledge manifest or local knowledge store. |
| `after_tasks` | `/speckit.tasks` | At least one `tasks.md` exists in supported locations (`specs/**`, `.specify/`, or workspace root), and checkbox format is validated. |
| `after_implement` | `/speckit.implement` | E2E test files exist and include assertions, then domain-specific validators run. Docker preflight connectivity is checked on every gate event when `execution_mode` is `docker-fallback`. |
| `after_review` | Review completion | All tasks are marked complete, no outstanding Tier 2 findings remain in gate feedback, and E2E assertions are still present. |

## Testing validation rules

During `after_implement`, the gate enforces baseline E2E testing hygiene:

- At least one E2E test file must exist.
- Allowed naming patterns:
  - `e2e_test_*.py`
  - `*.e2e-spec.ts`, `*.e2e-spec.js`
  - `*.e2e.test.ts`, `*.e2e.test.js`
- Each discovered E2E test file must include recognizable assertions (for
  example `assert` or `expect(...)`).

## Gate outcomes

- **Tier 1:** non-critical issues are written to `.specify/context/gate_feedback.md` and execution continues.
- **Tier 2:** critical issues are also written to `gate_feedback.md` and execution stops with a non-zero exit code.
- Tier 1 retries are tracked per `event + rule` and escalate to Tier 2 when a specific finding exceeds the retry limit (default: 3, configurable via `gate.max_tier1_retries` in `.itx-config.yml`).
- Findings can include confidence metadata (`deterministic` or `heuristic`) and remediation ownership for triage.
- By default, heuristic Tier 1 findings do not auto-escalate on retry unless `gate.heuristic_retry_escalates` is enabled.

## Passive guidance vs. active validation

The Python validators in `itx-gates` are thin tripwires that catch the most
egregious domain violations. They do not comprehensively enforce every rule
from the constitution or anti-pattern markdown files.

| Domain | What the validator checks | What is left to passive guidance |
|------|--------------------------|--------------------------------|
| `fintech-banking` | Raw PAN storage patterns; advisory warning when payment flow lacks explicit SCA markers | Double-entry correctness, ledger invariants, reconciliation, clock injection |
| `fintech-trading` | `float` money checks, idempotency-key checks, lifecycle-transition checks, hot-path blocking-I/O checks, replay-marker advisories | Full matching-engine determinism, cross-service sequencing guarantees |
| `healthcare` | PHI-specific variable names inside logging statements (`patient_name`, `ssn`, `dob`, etc.; opaque IDs like `patient_id` are allowed) | Consent checks, FHIR compliance, retention policies, audit trail completeness |
| `saas-platform` | Heuristic checks for tenant-scoped SQL without `tenant_id` and cache/redis literal keys that omit tenant namespace | Full RLS correctness, OIDC token validation, cross-tenant integration tests, SCIM |

The markdown patterns, design-patterns, and anti-patterns in `.specify/` guide
the AI agent's design-time reasoning. The Python gates provide a runtime safety
net for critical violations only.

## Rule-to-control matrix

This matrix defines how strongly each control is currently enforced:

| Control | Mechanism | Status |
|--------|-----------|--------|
| Plan structure and required sections | `after_plan` + `.specify/policy.yml` | **enforced** |
| Tasks presence and checkbox syntax | `after_tasks` validator | **enforced** |
| E2E test file and assertion baseline | `after_implement` generic checks | **enforced** |
| Completion readiness (all tasks done + no Tier 2 outstanding) | `after_review` generic checks | **enforced** |
| Domain tripwire checks (trading/banking/healthcare/saas-platform) | Domain validators in `hooks/validators/` | **enforced** |
| Banking payment invariants (`idempotency-key`, in-place ledger mutation) | Banking validator + policy `rules` metadata | **enforced** |
| Retry and escalation policy | Retry-state logic in `orchestrator.py` | **enforced** |
| Rule severity/confidence/remediation ownership metadata | `.specify/policy.yml` `rules` map + orchestrator normalization | **enforced** |
| Pattern/design guidance quality | Constitution + templates + pattern docs | **advisory** |
| End-to-end compliance assurance | Human review + governance process | **advisory** |
| Expanded semantic checks and precision upgrades | Roadmap hardening milestones | **planned** |

See `docs/adr/0003-two-layer-quality-enforcement.md` for the rationale behind this split.
