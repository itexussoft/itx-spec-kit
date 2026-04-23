# itexus-spec-kit

`itexus-spec-kit` is an Itexus delivery kit built on top of `github/spec-kit`.
Deterministic Context Routing for AI Agents combines:

- a base preset with templates, policy, governance files, and knowledge assets
- domain overlays for `fintech-trading`, `fintech-banking`, `healthcare`, and `saas-platform`
- local extensions for brownfield workflows and quality gates
- bootstrap and patch scripts that materialize everything into a downstream workspace

Current kit version: `0.4.1` from [catalog/index.json](/Users/sprivalov/itexus/src/itx-spec-kit/catalog/index.json).

**What It Gives You**

- Opinionated plan/templates for feature, patch, refactor, bugfix, migration, spike, modify, hotfix, and deprecate flows
- brownfield intake commands via [extensions/itx-brownfield-workflows/extension.yml](/Users/sprivalov/itexus/src/itx-spec-kit/extensions/itx-brownfield-workflows/extension.yml)
- Runtime quality gates via [extensions/itx-gates/extension.yml](/Users/sprivalov/itexus/src/itx-spec-kit/extensions/itx-gates/extension.yml)
- Deterministic Context Routing for AI Agents, with thresholded tag matching and anti-tag suppression to reduce prompt noise
- Workspace bootstrapping via [scripts/itx_init.py](/Users/sprivalov/itexus/src/itx-spec-kit/scripts/itx_init.py)
- Safe forward updates for existing workspaces via [scripts/patch.py](/Users/sprivalov/itexus/src/itx-spec-kit/scripts/patch.py)
- Opt-in architecture assurance, mutation testing, smell guidance, and temporal-fakes scaffolding

**Headline Feature: Deterministic Context Routing**

The JIT Context Router now promotes knowledge deterministically instead of relying on broad lexical overlap alone.

- Knowledge files can declare `tags` and `anti_tags` in frontmatter.
- The router scores positive matches from `tags`, subtracts penalties from `anti_tags`, and enforces a minimum relevance threshold before promoting a file into active `.specify/` context.
- This sharply reduces false positives such as backend ledger, saga, CLI, or tenant-isolation guidance being pulled into frontend React work just because a request contains overloaded words like `transaction`, `event`, `command`, or `context`.
- The result is smaller, cleaner prompt context for AI agents, with less prompt noise, fewer accidental architecture detours, and better retention of the task that actually matters.

**Quick Start**

Bootstrap a new workspace:

```bash
./init-scripts/itx-init.sh \
  --project-name "example-service" \
  --agent cursor \
  --domain fintech-trading \
  --workspace "/path/to/project" \
  --execution-mode mcp
```

Patch an existing workspace:

```bash
python3 scripts/patch.py --workspace /path/to/project
```

Validate this repo locally:

```bash
make test
make compile
make validate-catalog
```

**What Gets Installed Into a Workspace**

`itx-init` runs `specify init` first, then stages Itexus-owned files into the generated workspace:

- `.itx-config.yml` with domain, execution mode, hook mode, upstream `spec_kit_ref`, and primary agent
- `.specify/policy.yml` plus governance files like `decision-authority.yml`, `input-contracts.yml`, `notification-events.yml`, `workflow-state-schema.yml`, and `smell-catalog.yml`
- `.specify/templates/`, `.specify/pattern-index.md`, and knowledge assets
- `.specify/extensions/itx-gates` and `.specify/extensions/itx-brownfield-workflows`
- `docs/knowledge-base/` reference docs
- `harnesses/temporal-fakes/`, and `harnesses/docker-fallbacks/` when `--execution-mode docker-fallback`

`patch.py` keeps existing workspaces aligned with newly shipped kit assets. Kit-owned files are overwritten. User-editable files get `.kit-update` side files unless `--force` is used.

**Core Modes**

- `--domain`: `base`, `fintech-trading`, `fintech-banking`, `healthcare`, `saas-platform`
- `--knowledge-mode`: `lazy` or `eager`
- `--execution-mode`: `mcp` or `docker-fallback`
- `--hook-mode`: `auto`, `manual`, or `hybrid`

`lazy` knowledge mode stages pattern content into `.specify/.knowledge-store/` and promotes relevant files later. `eager` copies everything directly into active `.specify/` folders.
In `lazy` mode, deterministic routing uses `tags`, `anti_tags`, and a minimum relevance threshold to decide what the AI agent should actually load.

**Commands and Workflow**

Use upstream Spec Kit flow in this order:

1. `/speckit.constitution`
2. `/speckit.specify`
3. `/speckit.clarify` if needed
4. `/speckit.plan`
5. `/speckit.tasks`
6. `/speckit.analyze` if needed
7. `/speckit.implement`

For brownfield work, start with one of:

- `/speckit.bugfix`
- `/speckit.refactor`
- `/speckit.modify`
- `/speckit.hotfix`
- `/speckit.deprecate`

Those commands establish workstream metadata and then hand off to `/speckit.plan`.
They are not guaranteed upstream core commands; they are local intake helpers that route brownfield work into the standard planning flow.

**Quality Gates**

`itx-gates` runs after `after_plan`, `after_tasks`, `after_implement`, and `after_review`.
It writes gate artifacts under `.specify/context/`, including:

- `execution-brief.md`
- `gate_feedback.md`
- `gate-state.yml`
- `gate-events.jsonl`
- `last-gate-summary.md`
- optional architecture and mutation reports/baselines

The newer quality capabilities are opt-in in `.specify/policy.yml`:

- `quality.architecture`
- `quality.mutation_testing`

Recent additions also include:

- smell-to-refactoring guidance via `.specify/smell-catalog.yml`
- temporal fake harness examples under `harnesses/temporal-fakes/`

**Agent Notes**

If you are an AI agent working in a bootstrapped workspace:

- Read `.specify/context/execution-brief.md` first when it exists.
- Treat `.specify/policy.yml` as the workspace policy surface.
- Use `.itx-config.yml` for host/runtime settings such as `hook_mode`, `execution_mode`, and `spec_kit_ref`.
- Respect the current workstream under `specs/**` and avoid mixing unrelated slices.
- Prefer `patch.py` over manual copy/paste when updating an existing workspace from this repo.
- Run `make test`, `make compile`, and `make validate-catalog` after changing this kit.

**Project Shape**

Top-level directories:

- [presets/](/Users/sprivalov/itexus/src/itx-spec-kit/presets) for base and domain presets
- [extensions/](/Users/sprivalov/itexus/src/itx-spec-kit/extensions) for local Spec Kit extensions
- [scripts/](/Users/sprivalov/itexus/src/itx-spec-kit/scripts) for bootstrap, patching, validation, and release helpers
- [harnesses/](/Users/sprivalov/itexus/src/itx-spec-kit/harnesses) for reusable execution/test harnesses
- [docs/](/Users/sprivalov/itexus/src/itx-spec-kit/docs) for repo-level documentation, ADRs, and program notes
- [tests/](/Users/sprivalov/itexus/src/itx-spec-kit/tests) for regression coverage

Useful entry points:

- [scripts/itx_init.py](/Users/sprivalov/itexus/src/itx-spec-kit/scripts/itx_init.py)
- [scripts/patch.py](/Users/sprivalov/itexus/src/itx-spec-kit/scripts/patch.py)
- [scripts/validate_catalog.py](/Users/sprivalov/itexus/src/itx-spec-kit/scripts/validate_catalog.py)
- [Makefile](/Users/sprivalov/itexus/src/itx-spec-kit/Makefile)
- [docs/tech-radar-program.md](/Users/sprivalov/itexus/src/itx-spec-kit/docs/tech-radar-program.md)

**Prerequisites**

- Python 3.x
- Spec Kit CLI support through `spec-kit`, `specify`, or `uvx`
- Docker only when using `--execution-mode docker-fallback`

The base preset and local extensions currently target `speckit_version: ">=0.5.0"`.
