# itexus-spec-kit

Itexus accelerator for spec-driven AI delivery on top of `github/spec-kit`.

**Kit version** is declared in [`catalog/index.json`](catalog/index.json) as `kit.version` (currently **0.3.0**).

## What changed in 0.3.0

- **Wave E2 framing:** docs now explain the current architecture as an upstream-aligned `spec-kit` preset-plus-extension model instead of a parallel command ecosystem.
- **Migration guidance:** added `docs/migration-guide.md` and staged `docs/knowledge-base/migration-guide.md` so existing workspaces patched forward get an actionable old-to-new mapping.
- **Responsibility model:** README, knowledge-base docs, and extension manifests now consistently distinguish upstream core commands, brownfield intake extension commands, `itx-gates` hook execution, and community review/cleanup via `run_speckit.py`.
- **Gate runtime clarity:** host-facing guidance now explicitly points to `gatectl.py`, keeps `orchestrator.py` as the validator runtime, and documents `hook_mode`, `gate-state.yml`, `gate-events.jsonl`, and `last-gate-summary.md`.
- **Preset surface:** the base preset manifest now advertises the shipped `refactor-plan`, `bugfix-report`, and `execution-brief` templates.

## What changed in 0.2.2

- **Upstream default:** bootstrap and `uvx` flows pin **github/spec-kit `v0.5.0`** (override with `spec_kit_ref` in `.itx-config.yml` or `--spec-kit-ref` on init).
- **`specify init`:** `itx_init` passes **`--ignore-agent-tools`** so init does not require Codex/Claude/etc. on `PATH`.
- **Community extensions:** cloned extensions are sanitized to drop legacy command **aliases** that **specify-cli 0.5+** rejects (canonical command names unchanged).
- **Manifests:** presets and `itx-gates` declare **`speckit_version: ">=0.5.0"`** so older specify-cli installs are rejected at `preset add` / `extension add`.

## What changed in 0.2.1

- **Architectural pattern:** `asynchronous-event-loop-architecture.md` — single-process `asyncio` guidance for integration daemons (log watch, chat, HTTP sidecars), with Tool Plan and constitution cross-references; complements `cli-orchestrator-architecture.md` exit-and-resume defaults.

## What changed in 0.2.0

- **Governance foundation (agent autonomy):** base preset ships YAML contracts copied into `.specify/` on bootstrap and patch:
  - `decision-authority.yml` — decision rights (autonomous / propose / human)
  - `input-contracts.yml` — required and optional inputs and validation rules per workflow phase
  - `notification-events.yml` — lifecycle, gate, approval, and error notification contract
  - `workflow-state-schema.yml` — persisted workflow state for resumable runs
- **Knowledge base:** `delivery-mechanics.md` in the base preset docs (installed under `docs/knowledge-base/`); `index.md` indexes the governance artifacts above.
- **`after_review` gate:** new Spec-Kit hook runs completion checks after review — all tasks checked off, no outstanding Tier 2 findings in `gate_feedback.md`, E2E assertion baseline still satisfied.
- **Templates:** `done-report-template.md` for delivery traceability and merge handoff.
- **Init/patch:** governance YAML uses the same safe-update rules as `constitution.md`, `policy.yml`, and KB docs (`.kit-update` side files unless `--force`).

## What changed in 0.1.3

- Added E2E testing baseline enforcement in `itx-gates` (`after_implement`):
  - required E2E test file presence by naming convention
  - assertion-presence validation in discovered E2E files
- Added mandatory `## 13. Test Strategy` section for Full Plan validation (`after_plan`).
- Added QA/testing artifacts to the base preset:
  - `patterns/e2e-testing-strategy.md`
  - `templates/test-strategy-template.md`
  - `templates/qa-checklist-template.md`
- Updated constitution and knowledge-base docs to align implementation with test-first expectations.

## What is included

- Cross-platform bootstrap scripts: `init-scripts/itx-init.sh`, `init-scripts/itx-init.ps1`
- Base and domain presets:
  - `presets/base` — constitution, shared policy, governance YAML (`decision-authority.yml`, `input-contracts.yml`, `notification-events.yml`, `workflow-state-schema.yml`), templates, knowledge-base docs, and foundational architectural patterns
  - `presets/fintech-trading` — trading-specific constitution, constraints, and patterns (CQRS, cell-based HA); includes a **domain delivery brief** template so `specify preset add` meets specify-cli 0.5+ requirements
  - `presets/fintech-banking` — banking-specific constitution, constraints, and patterns (event-sourced ledger, sagas, PSD2 gateway); includes a **domain delivery brief** template for the same reason
  - `presets/healthcare` — healthcare-specific constitution, constraints, and patterns (FHIR facade, zero-trust PHI); includes a **domain delivery brief** template for the same reason
  - `presets/saas-platform` — multi-tenant SaaS constitution, constraints, and patterns (data isolation, OIDC/SSO, white-label BFF config); includes a **domain delivery brief** template for the same reason
- Shared policy manifest: `presets/base/policy.yml` — single source of truth for work-class rules consumed by the gate orchestrator
- Active quality-gate extension: `extensions/itx-gates`
- Brownfield workflow command extension: `extensions/itx-brownfield-workflows` (`/speckit.bugfix`, `/speckit.refactor`, `/speckit.modify`, `/speckit.hotfix`, `/speckit.deprecate`)
- Community extensions installed by default: `dsrednicki/spec-kit-cleanup`, `ismaelJimenez/spec-kit-review` (optional: `--with-jira` adds `spec-kit-jira`)
- Harnesses for Docker fallback execution
- Catalog metadata: `catalog/index.json`

## Repository structure

```
itexus-spec-kit/
├── catalog/
│   └── index.json
├── docs/
│   ├── adr/
│   ├── architecture-maintenance.md
│   ├── migration-guide.md
│   └── roadmap.md
├── extensions/
│   ├── itx-brownfield-workflows/
│   │   ├── commands/
│   │   └── extension.yml
│   └── itx-gates/
│       ├── commands/
│       ├── extension.yml
│       └── hooks/
│           └── validators/
├── harnesses/
│   └── docker-fallbacks/
├── init-scripts/
│   ├── itx-init.sh
│   └── itx-init.ps1
├── presets/
│   ├── base/
│   │   ├── constitution.md
│   │   ├── policy.yml
│   │   ├── decision-authority.yml
│   │   ├── input-contracts.yml
│   │   ├── notification-events.yml
│   │   ├── workflow-state-schema.yml
│   │   ├── docs/
│   │   ├── design-patterns/
│   │   ├── anti-patterns/
│   │   ├── patterns/
│   │   └── templates/
│   ├── fintech-trading/
│   │   ├── constitution.md
│   │   ├── docs/
│   │   ├── glossary.md
│   │   ├── design-patterns/
│   │   ├── anti-patterns/
│   │   └── patterns/
│   ├── fintech-banking/
│   │   └── (same structure as fintech-trading)
│   └── healthcare/
│       └── (same structure as fintech-trading)
│   └── saas-platform/
│       └── (same structure as fintech-trading)
├── scripts/
└── tests/
```

## Knowledge loading modes

During `itx-init`, the `--knowledge-mode` flag controls how pattern files are staged:

- **`lazy` (default):** Pattern, design-pattern, and anti-pattern markdown files are staged into `.specify/.knowledge-store/` (gitignored). They are **not** placed in the active `.specify/` directories until gate-time routing promotes relevant files. Routing is hybrid: explicit `selected_patterns` blocks remain supported, while plan/task keyword tags from `knowledge-manifest.json` drive default JIT hydration under a ~15,000 token budget per phase.
- **`eager`:** All pattern files are copied directly into `.specify/patterns/`, `.specify/design-patterns/`, and `.specify/anti-patterns/` during bootstrap. Best for teams that want full local availability without gate-driven hydration.

In both modes, `.specify/pattern-index.md` and `docs/knowledge-base/` workflow docs are always copied.

### Execution-brief (agent-light mode)

The orchestrator writes `.specify/context/execution-brief.md` as a compact
agent-facing summary after `after_plan`, then refreshes it after `after_tasks`
and `after_review`.

Progressive loading rule:

1. Read `execution-brief.md` first.
2. Load only files/patterns referenced by the brief.
3. Open raw control-plane artifacts (`policy.yml`, `input-contracts.yml`,
   `gate_feedback.md`, etc.) only when needed for investigation or explicit
   human request.

## Pattern selection in plans

Plans declare which knowledge files they need using a structured HTML comment:

```markdown
<!-- selected_patterns: domain-driven-design.md, hexagonal-architecture.md -->
```

Patch plans that do not require patterns use:

```markdown
<!-- selected_patterns: none -->
```

For backward compatibility the gate also recognizes inline backtick references to `*.md` filenames. The structured block is preferred.

## Architectural patterns

**Base patterns** (always included): Foundational Principles (KISS/YAGNI/DRY/SOLID), Domain-Driven Design, Hexagonal Architecture, Clean Architecture, Modular Monolith, Event-Driven Microservices, Transactional Outbox, E2E Testing Strategy, CLI Orchestrator Architecture, Asynchronous Event Loop Architecture.

For tool-class projects (CLI tools, workflow engines, automation scripts), use
the **Tool Plan** path from the constitution and prefer
`cli-orchestrator-architecture.md` over DDD tactical layering.

**Domain patterns** (added per domain selection):

| Domain | Patterns |
|--------|---------|
| `fintech-trading` | CQRS Order Sequencing, High-Availability Cell-Based Architecture |
| `fintech-banking` | Event-Sourced Ledger, Saga Distributed Transactions, PSD2 API Gateway |
| `healthcare` | FHIR Facade, Zero-Trust PHI Boundary |
| `saas-platform` | Multi-Tenant Data Isolation, Federated Identity (OIDC), White-Label Theming Architecture |

## Prerequisites

- Python 3.x
- Docker / Docker Compose (required only for `--execution-mode docker-fallback`)
- Spec Kit CLI: `specify` (install via [Spec Kit installation](https://github.github.com/spec-kit/installation.html)), or `uvx` (init scripts can use `uvx` when `specify` is not on `PATH`)
- When `uvx` is used, bootstrap pins upstream `github/spec-kit` to `v0.5.0` by default. Override with `--spec-kit-ref <tag-or-sha>` when needed. Existing workspaces may keep `spec_kit_ref: "v0.4.3"` in `.itx-config.yml` until you intentionally upgrade.

## Dependency management

- Runtime dependencies are pinned in `extensions/itx-gates/requirements.txt` and mirrored in `pyproject.toml`.
- Dev/CI quality tooling is pinned in `requirements-dev.txt` and mirrored in `pyproject.toml` optional `dev` extras.
- To update dependencies, bump versions intentionally in both files and run:
  - `make compile`
  - `make test`
  - `make validate-catalog`

## Spec Kit workflow order (slash commands)

Align with **`github/spec-kit`** so optional steps are not run in the wrong order:

| Order | Command | Notes |
|------|---------|--------|
| 1 | `/speckit.constitution` | |
| 2 | `/speckit.specify` | |
| 3 | `/speckit.clarify` | optional |
| 4 | `/speckit.plan` | |
| 5 | **`/speckit.tasks`** | **Creates `tasks.md`** under the active workstream (e.g. `specs/.../tasks.md`) |
| 6 | `/speckit.analyze` | optional; **requires `tasks.md`** — run only **after** step 5 |
| 7 | `/speckit.implement` | |

For brownfield work, run the relevant intake command first (`/speckit.bugfix`,
`/speckit.refactor`, `/speckit.modify`, `/speckit.hotfix`,
`/speckit.deprecate`), then continue with `/speckit.plan`.

If **`/speckit.analyze`** reports that **`tasks.md` is missing**, run **`/speckit.tasks`** first and confirm the file exists in the active workstream folder.

After implementation, use your review/cleanup extensions as needed. When the review pass is complete, run the **`after_review`** gate so completion readiness is validated before merge (see [Gate orchestration](#gate-orchestration)).

## Bootstrap usage

### POSIX

```bash
./init-scripts/itx-init.sh \
  --project-name "example-service" \
  --agent cursor \
  --domain fintech-trading \
  --spec-kit-ref v0.5.0 \
  --workspace "/path/to/project" \
  --execution-mode docker-fallback \
  --with-jira
```

`--agent` accepts any **specify-cli** integration key pinned for [github/spec-kit `v0.5.0`](https://github.com/github/spec-kit/tree/v0.5.0) (see [`scripts/itx_specify.py`](scripts/itx_specify.py) for the exact set). Convenience aliases match upstream: `cursor` → `cursor-agent`, `kiro` → `kiro-cli`. For **`generic`**, pass **`--generic-commands-dir`** (for example `.myagent/commands/`). Generic bootstrap requires **specify** or **uvx** (not the `spec-kit` binary). On success, `.itx-config.yml` records `agents.primary` as the canonical integration key. The bootstrap also records `hook_mode` (`hybrid` by default) so manual-host wrappers know whether to trust auto hooks or actively ensure them.

### PowerShell

```powershell
.\init-scripts\itx-init.ps1 `
  --project-name "example-service" `
  --agent cursor `
  --domain fintech-trading `
  --spec-kit-ref v0.5.0 `
  --workspace "C:\work\example-service" `
  --execution-mode docker-fallback `
  --with-jira
```

## Community extension runner (review & cleanup)

Community extensions (`ismaelJimenez/spec-kit-review`, `dsrednicki/spec-kit-cleanup`) are installed during bootstrap using pinned refs and require the Spec-Kit CLI at runtime. The universal runner adapter resolves the CLI automatically (`spec-kit` → `specify` → `uvx`) so these commands work in any environment, including Cursor's agent shell.

Brownfield entry commands (`/speckit.bugfix`, `/speckit.refactor`, `/speckit.modify`, `/speckit.hotfix`, `/speckit.deprecate`) are shipped by the local `itx-brownfield-workflows` extension. Treat them as extension-provided brownfield intake commands, not guaranteed upstream core commands.

Each brownfield intake command establishes or updates workstream metadata
(`workstream_id`, `work_class`, `artifact_root`, `branch`, optional
`parent_feature`) and then hands off to `/speckit.plan`. `/speckit.plan`
remains responsible for creating the dedicated planning artifact for that slice
(`bugfix-report.md`, `refactor-plan.md`, `modify-plan.md`, `hotfix-report.md`,
`deprecate-plan.md`).

The runner adapter is intended for extension commands (`review.run`, `cleanup.run`) only. Core workflow slash commands like `/speckit.plan` should be run directly in the agent chat, not through the adapter.

```bash
# Run review
python .specify/extensions/itx-gates/commands/run_speckit.py \
  --command review.run --workspace .

# Run cleanup
python .specify/extensions/itx-gates/commands/run_speckit.py \
  --command cleanup.run --workspace .
```

Cursor rules in `.cursor/rules/itx-speckit-commands.mdc` teach the AI agent to use the runner adapter automatically when the user invokes `/speckit.review.run` or `/speckit.cleanup.run`.

Legacy pseudo-command docs like `review_run.md` and `cleanup_run.md` are intentionally not part of the command surface.

## Patching already-bootstrapped projects

To apply updates from a newer version of `itexus-spec-kit` to an existing project without re-running the full bootstrap:

```bash
python scripts/patch.py --workspace /path/to/project
```

The patch script is idempotent and distinguishes two file categories:

**Kit-owned** (always overwritten safely):
- `itx-gates` extension code (hooks, commands, runner adapter)
- Cursor rules

**User-editable** (may have been modified by `/speckit.constitution` or manual edits):
- `.specify/constitution.md`
- `.specify/policy.yml`
- `.specify/decision-authority.yml`, `.specify/input-contracts.yml`, `.specify/notification-events.yml`, `.specify/workflow-state-schema.yml`
- `docs/knowledge-base/*.md`

By default, user-editable files are **never overwritten**. If the kit has a newer version, it is written as a `.kit-update` side-file (e.g., `constitution.md.kit-update`). Review the diff and merge manually:

```bash
diff .specify/constitution.md .specify/constitution.md.kit-update
```

To force-overwrite user-editable files (creates `.patch-backup` first):

```bash
python scripts/patch.py --workspace /path/to/project --force
```

The script also appends `spec_kit_ref` and `hook_mode` to `.itx-config.yml` if missing.

To specify a custom kit source:

```bash
python scripts/patch.py --workspace /path/to/project --kit-root /path/to/itexus-spec-kit
```

### Switching or adding an AI integration (without full re-init)

These modes require **specify** or **uvx** on `PATH` (not `spec-kit`). They run the normal patch pass afterward so `itx-gates` and Cursor rules stay current.

**`--retarget-ai`** runs `specify init --here` for the given integration, then **restores** preserved paths so Itexus and local edits survive:

- `.specify/constitution.md`, `.specify/memory/constitution.md` (if present), `.specify/pattern-index.md`, `.specify/policy.yml`, governance YAML under `.specify/`, the base `docs/knowledge-base/*.md` files listed in the patch script, **`.specify/extensions/`** (community extensions and `itx-gates`), and by default **`.specify/templates/`**. Use **`--retarget-ai-refresh-templates`** to allow specify to refresh templates instead of restoring them.

After the normal patch pass, it also appends the retargeted integration key to `agents.installed` (if missing), updates `agents.primary`, then **re-runs** the same extension add steps as `itx-init` (local kit extensions plus pinned community review/cleanup), **materializes** any extension command prompts into that agent's `workflows/` folder when missing, and **mirrors** `.specify/extensions/.registry` command lists onto the retargeted integration key when needed. Use **`--skip-add-ai-extension-sync`** to skip that extension re-sync.

`generic` is **not** supported for `--retarget-ai` (use a concrete integration key).

```bash
python scripts/patch.py --workspace /path/to/project --retarget-ai claude
```

**`--add-ai`** runs `specify init` in a **temporary** directory and copies only that agent’s artifact tree (from `AGENT_CONFIG` when specify-cli is importable, else a built-in map) into the workspace—**best-effort multi-agent**. It appends the integration key to `agents.installed` in `.itx-config.yml`. After the normal patch pass, it **re-runs** the same extension add steps as `itx-init` (local kit extensions plus pinned community review/cleanup), then **materializes** any extension command prompts into that agent’s `workflows/` folder when missing, and **mirrors** `.specify/extensions/.registry` command lists onto the new integration key when needed (so tools that only read per-agent entries see extension commands). Use **`--skip-add-ai-extension-sync`** to skip extension install, materialization, and registry mirror (offline or scaffold-only). Upstream `.specify/integration.json` still describes a single primary agent; review overlaps (for example `.agents/`, `.github/`) manually.

```bash
python scripts/patch.py --workspace /path/to/project --add-ai kiro-cli
python scripts/patch.py --workspace /path/to/project --add-ai generic --generic-commands-dir .myagent/commands/
python scripts/patch.py --workspace /path/to/project --add-ai kilocode --skip-add-ai-extension-sync
```

## Gate orchestration

`extensions/itx-gates/hooks/orchestrator.py` implements the core validators, while `extensions/itx-gates/hooks/gatectl.py` is the host-friendly wrapper used by the `after_*` commands:

- Tier 1 (auto-correction): writes `.specify/context/gate_feedback.md` and exits `0`
- Tier 1 auto-retry contract: `gatectl.py ensure` writes `.specify/context/gate-failure-report.md` with `<SYSTEM_CORRECTION>` plus retry metadata (`retry_requested`, attempt counts, remaining budget)
- Tier 2 (hard halt): writes `.specify/context/gate_feedback.md` and exits `1`
- machine-readable state: writes `.specify/context/gate-state.yml` and appends `.specify/context/gate-events.jsonl`
- user-visible summary: refreshes `.specify/context/last-gate-summary.md`
- `after_plan`: validates mandatory plan sections (Full Plan requires sections `4`, `4b`, `5`, and `13`; Patch Plan and Tool Plan use patch-plan requirements `1` and `2`)
- `after_plan` / `after_tasks` / `after_review`: refresh `.specify/context/execution-brief.md` (additive, non-blocking)
- `after_tasks`: requires at least one tasks file in supported locations and emits Tier 1 when a tasks file has bare list items (all task items must use checkbox syntax)
- `after_implement`: validates E2E test presence/assertions before domain validators (including provider-based SAST for fintech-banking)
- `after_review`: validates delivery readiness (all tasks completed, no outstanding Tier 2 findings in gate feedback, E2E assertion baseline still met)
- pre-action audit log: appends `.specify/context/audit-log.md` entries only for high-risk actions (major refactor, package install/remove, high-risk ops/runtime changes)

Gate enforcement rules (mandatory sections, placeholder markers, retry limits) are loaded from `.specify/policy.yml`, which is copied from `presets/base/policy.yml` during bootstrap.

Canonical lifecycle:

- Feature flow:
  `/speckit.specify` -> `/speckit.plan` -> `after_plan` -> `/speckit.tasks` -> `after_tasks` -> `/speckit.implement` -> `after_implement` -> review -> `after_review`
- Brownfield flow:
  `/speckit.refactor|bugfix|modify|hotfix|deprecate` -> `/speckit.plan` -> `after_plan` -> `/speckit.tasks` -> `after_tasks` -> `/speckit.implement` -> `after_implement` -> review -> `after_review`

Host caveat:

- In environments that truly honor Spec-Kit extension hooks, `after_*` gates may fire automatically.
- In plain AI shells or UI wrappers where hook execution is not guaranteed, the agent must run `gatectl.py ensure` manually after each phase boundary. `gatectl` reruns the orchestrator only when state is stale or missing and otherwise preserves the last fresh result.

Invocation examples:

```bash
python extensions/itx-gates/hooks/gatectl.py ensure --event after_implement --workspace /path/to/project
python extensions/itx-gates/hooks/gatectl.py ensure --event after_review --workspace /path/to/project
python extensions/itx-gates/hooks/gatectl.py ensure --event after_plan --workspace /path/to/project --json
```

For migration mapping from legacy feature/patch-only usage to the current workstream and extension model, see `docs/migration-guide.md`.

## Assurance boundaries and control coverage

`itexus-spec-kit` uses a two-layer model:

- **Passive guidance:** constitutions, patterns, anti-patterns, templates.
- **Active validation:** deterministic gate checks at workflow boundaries.

This means not every constitution rule is currently executable in validators.
The matrix below defines current coverage and should be used as the source of
truth when assessing delivery assurance.

| Control area | Current mechanism | Status |
|-------------|-------------------|--------|
| Plan presence and mandatory plan sections | `after_plan` gate in `orchestrator.py` (policy-driven) | **enforced** |
| Tasks file presence and checkbox format | `after_tasks` gate in `orchestrator.py` | **enforced** |
| E2E test file presence and assertion baseline | `after_implement` gate in `orchestrator.py` | **enforced** |
| Completion readiness after review (tasks done, no Tier 2 outstanding, E2E still present) | `after_review` gate in `orchestrator.py` | **enforced** |
| Tiered retry/escalation behavior | `orchestrator.py` + `.specify/policy.yml` | **enforced** |
| Trading float money tripwire | `validators/trading_ast.py` | **enforced** |
| Trading entrypoint idempotency and lifecycle/hot-path checks | `validators/trading_ast.py` + policy rule mapping | **enforced** |
| Banking PCI/SCA heuristic tripwires | `validators/banking_heuristic.py` | **enforced** |
| Banking idempotency-key and in-place ledger mutation checks | `validators/banking_heuristic.py` + policy rule mapping | **enforced** |
| Healthcare PHI logging heuristic tripwires | `validators/health_regex.py` | **enforced** |
| SaaS tenant-scoped query / cache key heuristic tripwires | `validators/saas_platform_heuristic.py` | **enforced** |
| DDD correctness and complete architecture quality | Constitution + pattern guidance | **advisory** |
| Full compliance proof (PCI/PSD2/HIPAA) | Constitution + domain docs + human review | **advisory** |
| Full multi-tenant isolation proof (RLS, cross-tenant tests) | Constitution + domain docs + human review | **advisory** |
| Broader semantic validator coverage and stronger precision | Roadmap Milestone 1 / Milestone 5 | **planned** |

## Security controls matrix

| Control | Local | CI | Release |
|--------|-------|----|---------|
| Lint + type checks | recommended | required | required |
| Dependency vulnerability audit (`pip-audit`) | recommended | required | required |
| Secret scanning (`gitleaks`) | recommended | required | required |
| License policy check (`pip-licenses --allow-only`) | optional | required | required |
| Unit test suite | required | required | required |

## Rule metadata in policy

`presets/base/policy.yml` now carries per-rule metadata under `rules`:

- `severity`
- `confidence` (`deterministic` or `heuristic`)
- `remediation_owner`

Gate feedback surfaces this metadata to make triage and ownership explicit.

## Run tests/checks

### Task runners

- POSIX: `make help`
- PowerShell: `.\scripts\tasks.ps1 -Task test`

### Python syntax check

```bash
make compile
```

### Unit tests

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

### Example gate run

```bash
python3 extensions/itx-gates/hooks/orchestrator.py --event after_implement --workspace /path/to/project
```

## Build catalog artifacts

```bash
python3 scripts/build_catalog_artifacts.py
```

This command:

1. validates `catalog/index.json` against all preset/extension manifests
2. builds zip artifacts into `dist/`
3. keeps artifact names aligned with current catalog version

### Bump release version

```bash
python3 scripts/release.py --version 0.3.0
```

With artifact rebuild:

```bash
python3 scripts/release.py --version 0.3.0 --build
```

PowerShell equivalent:

```powershell
.\scripts\tasks.ps1 -Task release -Version 0.3.0
.\scripts\tasks.ps1 -Task build-artifacts
```

## Docker fallback requirement

Docker fallback currently performs a sandbox/container availability preflight via `docker exec` against the configured container. Full in-container validator and CLI execution is planned as future hardening work.

## CI

- `.github/workflows/ci.yml` runs compile checks, unit tests, and catalog validation on push/PR.
- It verifies that generated `pattern-index.md` files are up to date.
- Scheduled workflow includes upstream drift detection against latest `github/spec-kit` main.

## Contributing

See `CONTRIBUTING.md` for the local validation and release checklist.

## Architecture decisions

See `docs/adr/` for accepted design decisions, including:

- Python-only cross-platform hook runtime
- Tiered gate state machine (Tier 1 auto-correction vs Tier 2 hard halt)
- Shared policy manifest for single-source-of-truth gate enforcement

For script ownership boundaries and reproducibility maintenance policy, see `docs/architecture-maintenance.md`.

## Roadmap

See `docs/roadmap.md` for status-driven milestones.

Current focus:

- Gate Engine Hardening (validator precision, severity mapping, remediation diagnostics)
- Upstream Drift E2E Matrix (compatibility checks vs `github/spec-kit` main + pinned baseline)
- Bootstrap UX and reliability improvements

Already shipped baseline:

- **0.3.0** — Wave E2 docs/migration/productization alignment, staged migration guide, clearer gate/runtime ownership model, base preset template surface advertised in manifests
- **0.2.2** — default **spec-kit `v0.5.0`**, `--ignore-agent-tools` on init, community extension alias sanitization for specify-cli 0.5+, `speckit_version >=0.5.0` on kit artifacts
- **0.2.1** — `asynchronous-event-loop-architecture.md` pattern for asyncio integration daemons; Tool Plan constitution alignment
- **0.2.0** — governance YAML in `.specify/`, `after_review` gate, `delivery-mechanics.md`, `done-report-template.md`, init/patch staging for autonomy contracts
- **0.1.3** — E2E and QA foundation (mandatory test strategy section, E2E gate checks, QA/testing templates)
