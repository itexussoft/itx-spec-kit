# Workflow and Gates

Delivery stages:

1. Constitution (`/speckit.constitution`)
2. Specify (`/speckit.specify`)
3. Clarify (`/speckit.clarify`, optional)
4. Select the correct planning entry path for the active work item.
   - Feature flow: `/speckit.specify` -> `/speckit.plan`
   - Brownfield flow: `/speckit.bugfix`, `/speckit.refactor`, `/speckit.modify`, `/speckit.hotfix`, or `/speckit.deprecate` -> `/speckit.plan`
   - Brownfield intake commands establish workstream metadata (`workstream_id`, `work_class`, `artifact_root`, `branch`, optional `parent_feature`) before `/speckit.plan`.
   - `/speckit.plan` reads `.specify/pattern-index.md`, selects relevant pattern files, and produces the planning artifact mapped to the resolved work class.
   - In lazy knowledge mode, read full candidate pattern content from `.specify/.knowledge-store/` during planning.
5. **`after_plan` gate** — validates plan presence + mandatory sections; in lazy knowledge mode, materializes only selected pattern files into `.specify/`
5b. **Execution brief refresh** — after plan/tasks/review checks, the orchestrator updates `.specify/context/execution-brief.md` as a compact agent-facing summary (additive, non-blocking).
6. Tasks (`/speckit.tasks`) — produces **`tasks.md`** in the active workstream directory using `tasks-template.md` as format reference. Every task **must** use `- [ ]` checkbox syntax.
7. **`after_tasks` gate** — validates tasks file presence and checkbox format
8. Analyze (`/speckit.analyze`, optional) — **only after** `tasks.md` exists; cross-artifact check needs the task inventory
9. Implement (`/speckit.implement`)
10. **`after_implement` gate** — validates E2E test presence and assertion quality, then runs domain-specific validators
11. Test / Cleanup / Review (extensions + gates)
12. **`after_review` gate** — validates delivery readiness (all tasks completed, no outstanding Tier 2 feedback, E2E checks still present)
13. Deliver — prepare done report and open PR for human merge decision

## Canonical lifecycle

### Feature flow

1. `/speckit.constitution` once per project or when project rules truly change
2. `/speckit.specify`
3. `/speckit.clarify` when needed
4. `/speckit.plan`
5. `after_plan`
6. `/speckit.tasks`
7. `after_tasks`
8. `/speckit.analyze` optional
9. `/speckit.implement`
10. `after_implement`
11. `/speckit.review.run` or equivalent review flow
12. `after_review`
13. `/speckit.cleanup.run` when needed
14. deliver / done report / PR

### Brownfield flow

1. Choose the right intake command:
   - `/speckit.refactor`
   - `/speckit.bugfix`
   - `/speckit.modify`
   - `/speckit.hotfix`
   - `/speckit.deprecate`
2. The intake command establishes or updates:
   - `workstream_id`
   - `work_class`
   - `artifact_root`
   - `branch`
   - optional `parent_feature`
3. `/speckit.plan`
4. `after_plan`
5. `/speckit.tasks` when required or useful for that work class
6. `after_tasks`
7. `/speckit.analyze` optional
8. `/speckit.implement`
9. `after_implement`
10. `/speckit.review.run` or equivalent review flow
11. `after_review`
12. `/speckit.cleanup.run` when needed
13. deliver / done report / PR

### Host capability rule

If the current host truly supports Spec-Kit extension hooks, the `after_*`
gates should fire automatically. In plain AI shells or UI wrappers where hook
execution is not guaranteed, the agent must invoke `gatectl.py ensure`
manually after each corresponding phase boundary. The wrapper reruns the
orchestrator only when gate state is stale or missing and otherwise preserves
the last fresh result.

Brownfield entry commands (`/speckit.bugfix`, `/speckit.refactor`,
`/speckit.modify`, `/speckit.hotfix`, `/speckit.deprecate`) are delivered by
the local `itx-brownfield-workflows` extension. Treat them as
extension-provided brownfield intake commands, not guaranteed upstream core
commands.

These commands do not replace `/speckit.plan`. They prepare the active
workstream and then route into `/speckit.plan`, which creates the correct
planning artifact for the resolved work class.

### Command ownership and adapters

- Upstream core commands (`/speckit.constitution`, `/speckit.specify`,
  `/speckit.clarify`, `/speckit.plan`, `/speckit.tasks`, `/speckit.analyze`,
  `/speckit.implement`) should be run directly in agent chat.
- Brownfield intake commands (`/speckit.bugfix`, `/speckit.refactor`,
  `/speckit.modify`, `/speckit.hotfix`, `/speckit.deprecate`) are delivered by
  `itx-brownfield-workflows` and route into `/speckit.plan`.
- Community review and cleanup commands should run through
  `.specify/extensions/itx-gates/commands/run_speckit.py`.
- Gate lifecycle hooks should run through
  `.specify/extensions/itx-gates/hooks/gatectl.py ensure`.

Legacy pseudo-command docs (`review_run.md`, `cleanup_run.md`) are not part of
the current command surface.

If **`/speckit.analyze` is blocked** with "tasks.md not found", run
**`/speckit.tasks`** again (and ensure the required plan artifacts exist for
that workstream).

## Progressive loading rule

Use this order during implementation:

1. Read `.specify/context/execution-brief.md` first.
2. Load only artifacts and pattern files referenced by the brief.
3. Open raw control-plane files (`policy.yml`, `input-contracts.yml`, `gate_feedback.md`, etc.) only when needed for gate investigation, unblock, or explicit human request.

`execution-brief.md` is also the active context snapshot for the current workstream. Keep this lightweight and avoid adding a second memory-bank orchestration model.

## Lightweight micro-overlays

Micro-overlays are additive guidance, not new workflows:

- ACL overlay: apply when plans touch third-party/legacy boundaries; keep vendor models/errors inside adapters.
- Security overlays: apply selectively for auth/secrets, OWASP trust boundaries, and rate-limiting concerns.
- TDD overlay: prefer red-green-refactor for bugfix/refactor and modify-style behavior changes.
- Review/janitor overlays: stay risk-first in review and evidence-driven in cleanup while continuing to use `/speckit.review.run` and `/speckit.cleanup.run`.

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
| `after_plan` | `/speckit.plan` | Plan file exists; required sections for the resolved work-class policy are present with non-placeholder content; required traceability mode/id contract is valid. In lazy mode, selected pattern filenames are resolved from the knowledge manifest or local knowledge store. |
| `after_tasks` | `/speckit.tasks` | At least one `tasks.md` exists in supported locations (`specs/**`, `.specify/`, or workspace root), and checkbox format is validated. |
| `after_implement` | `/speckit.implement` | E2E test files exist and include assertions for work classes whose testing expectation is not `advisory`, then domain-specific validators run. Docker preflight connectivity is checked on every gate event when `execution_mode` is `docker-fallback`. |
| `after_review` | Review completion | All tasks are marked complete, no outstanding Tier 2 findings remain in gate feedback, and E2E assertions are still present. |

Execution-brief generation is intentionally additive and does not change gate pass/fail semantics.

## Gate state and host reliability

- `.itx-config.yml` records `hook_mode` (`hybrid` by default).
- `.specify/context/gate-state.yml` stores the latest machine-readable gate snapshot.
- `.specify/context/gate-events.jsonl` appends an event log for every gate execution.
- `.specify/context/last-gate-summary.md` stores the latest human-readable result.
- In manual or hybrid hosts, prefer:

```bash
python .specify/extensions/itx-gates/hooks/gatectl.py ensure --event after_plan --workspace .
```

- Add `--json` when the host or wrapper can consume structured output directly.

## Testing validation rules

During `after_implement`, the gate enforces baseline E2E testing hygiene for non-advisory work classes:

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
- Every gate execution also refreshes `gate-state.yml` and `last-gate-summary.md`, so hosts that hide shell output still have a durable result surface.
- Tier 1 retries are tracked per `event + rule` and escalate to Tier 2 when a specific finding exceeds the retry limit (default: 3, configurable via `gate.max_tier1_retries` in `.itx-config.yml`).
- Findings can include confidence metadata (`deterministic` or `heuristic`) and remediation ownership for triage.
- By default, heuristic Tier 1 findings do not auto-escalate on retry unless `gate.heuristic_retry_escalates` is enabled.
- Pre-action audit log entries are appended only for high-risk planned actions: major refactors, package install/remove activity, and high-risk ops/runtime changes.
- Traceability frontmatter is validated by work class using `traceability_mode` + matching id (`requirement_id`, `invariant_id`, `risk_id`, `incident_id`, `adr_id`).

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
