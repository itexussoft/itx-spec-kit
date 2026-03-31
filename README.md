# itexus-spec-kit

Itexus accelerator for spec-driven AI delivery on top of `github/spec-kit`.

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
  - `presets/base` — constitution, templates, knowledge-base docs, and foundational architectural patterns
  - `presets/fintech-trading` — trading-specific constitution, constraints, and patterns (CQRS, cell-based HA)
  - `presets/fintech-banking` — banking-specific constitution, constraints, and patterns (event-sourced ledger, sagas, PSD2 gateway)
  - `presets/healthcare` — healthcare-specific constitution, constraints, and patterns (FHIR facade, zero-trust PHI)
- Shared policy manifest: `presets/base/policy.yml` — single source of truth for plan tier rules consumed by the gate orchestrator
- Active quality-gate extension: `extensions/itx-gates`
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
│   └── roadmap.md
├── extensions/
│   └── itx-gates/
│       ├── commands/
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
├── scripts/
└── tests/
```

## Knowledge loading modes

During `itx-init`, the `--knowledge-mode` flag controls how pattern files are staged:

- **`lazy` (default):** Pattern, design-pattern, and anti-pattern markdown files are staged into `.specify/.knowledge-store/` (gitignored). They are **not** placed in the active `.specify/` directories until the `after_plan` gate promotes files that the plan explicitly selects. A `knowledge-manifest.json` is generated for structured hydration.
- **`eager`:** All pattern files are copied directly into `.specify/patterns/`, `.specify/design-patterns/`, and `.specify/anti-patterns/` during bootstrap. Best for teams that want full local availability without gate-driven hydration.

In both modes, `.specify/pattern-index.md` and `docs/knowledge-base/` workflow docs are always copied.

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

**Base patterns** (always included): Domain-Driven Design, Hexagonal Architecture, Clean Architecture, Modular Monolith, Event-Driven Microservices, Transactional Outbox.

**Domain patterns** (added per domain selection):

| Domain | Patterns |
|--------|---------|
| `fintech-trading` | CQRS Order Sequencing, High-Availability Cell-Based Architecture |
| `fintech-banking` | Event-Sourced Ledger, Saga Distributed Transactions, PSD2 API Gateway |
| `healthcare` | FHIR Facade, Zero-Trust PHI Boundary |

## Prerequisites

- Python 3.x
- Docker / Docker Compose (required only for `--execution-mode docker-fallback`)
- Spec Kit CLI: `specify` (install via [Spec Kit installation](https://github.github.com/spec-kit/installation.html)), or `uvx` (init scripts can use `uvx` when `specify` is not on `PATH`)
- When `uvx` is used, bootstrap pins upstream `github/spec-kit` to `v0.4.3` by default. Override with `--spec-kit-ref <tag-or-sha>` when needed.

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
| 5 | **`/speckit.tasks`** | **Creates `tasks.md`** under the active feature (e.g. `specs/.../tasks.md`) |
| 6 | `/speckit.analyze` | optional; **requires `tasks.md`** — run only **after** step 5 |
| 7 | `/speckit.implement` | |

If **`/speckit.analyze`** reports that **`tasks.md` is missing**, run **`/speckit.tasks`** first and confirm the file exists in that feature folder.

## Bootstrap usage

### POSIX

```bash
./init-scripts/itx-init.sh \
  --project-name "example-service" \
  --agent cursor \
  --domain fintech-trading \
  --spec-kit-ref v0.4.3 \
  --workspace "/path/to/project" \
  --execution-mode docker-fallback \
  --with-jira
```

### PowerShell

```powershell
.\init-scripts\itx-init.ps1 `
  --project-name "example-service" `
  --agent cursor `
  --domain fintech-trading `
  --spec-kit-ref v0.4.3 `
  --workspace "C:\work\example-service" `
  --execution-mode docker-fallback `
  --with-jira
```

## Community extension runner (review & cleanup)

Community extensions (`ismaelJimenez/spec-kit-review`, `dsrednicki/spec-kit-cleanup`) are installed during bootstrap using pinned refs and require the Spec-Kit CLI at runtime. The universal runner adapter resolves the CLI automatically (`spec-kit` → `specify` → `uvx`) so these commands work in any environment, including Cursor's agent shell.

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
- `docs/knowledge-base/*.md`

By default, user-editable files are **never overwritten**. If the kit has a newer version, it is written as a `.kit-update` side-file (e.g., `constitution.md.kit-update`). Review the diff and merge manually:

```bash
diff .specify/constitution.md .specify/constitution.md.kit-update
```

To force-overwrite user-editable files (creates `.patch-backup` first):

```bash
python scripts/patch.py --workspace /path/to/project --force
```

The script also appends `spec_kit_ref` to `.itx-config.yml` if missing.

To specify a custom kit source:

```bash
python scripts/patch.py --workspace /path/to/project --kit-root /path/to/itexus-spec-kit
```

## Gate orchestration

`extensions/itx-gates/hooks/orchestrator.py` implements:

- Tier 1 (auto-correction): writes `.specify/context/gate_feedback.md` and exits `0`
- Tier 2 (hard halt): writes `.specify/context/gate_feedback.md` and exits `1`
- `after_plan`: validates mandatory plan sections (Full Plan requires sections `4`, `4b`, `5`, and `13`)
- `after_tasks`: requires at least one tasks file in supported locations and emits Tier 1 when a tasks file has bare list items (all task items must use checkbox syntax)
- `after_implement`: validates E2E test presence/assertions before domain validators

Gate enforcement rules (mandatory sections, placeholder markers, retry limits) are loaded from `.specify/policy.yml`, which is copied from `presets/base/policy.yml` during bootstrap.

Invocation contract:

```bash
python extensions/itx-gates/hooks/orchestrator.py --event=after_implement --workspace=/path/to/project
```

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
| Tiered retry/escalation behavior | `orchestrator.py` + `.specify/policy.yml` | **enforced** |
| Trading float money tripwire | `validators/trading_ast.py` | **enforced** |
| Trading entrypoint idempotency and lifecycle/hot-path checks | `validators/trading_ast.py` + policy rule mapping | **enforced** |
| Banking PCI/SCA heuristic tripwires | `validators/banking_heuristic.py` | **enforced** |
| Banking idempotency-key and in-place ledger mutation checks | `validators/banking_heuristic.py` + policy rule mapping | **enforced** |
| Healthcare PHI logging heuristic tripwires | `validators/health_regex.py` | **enforced** |
| DDD correctness and complete architecture quality | Constitution + pattern guidance | **advisory** |
| Full compliance proof (PCI/PSD2/HIPAA) | Constitution + domain docs + human review | **advisory** |
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
python3 scripts/release.py --version 0.2.0
```

With artifact rebuild:

```bash
python3 scripts/release.py --version 0.2.0 --build
```

PowerShell equivalent:

```powershell
.\scripts\tasks.ps1 -Task release -Version 0.2.0
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

- E2E and QA foundation in `0.1.3` (mandatory test strategy section, E2E gate checks, and QA/testing templates)
