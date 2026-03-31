# Contributing to itexus-spec-kit

## Prerequisites

- Python 3.x
- Docker / Docker Compose
- Spec Kit CLI: `specify` (via [Spec Kit installation](https://github.github.com/spec-kit/installation.html)), `spec-kit`, or `uvx`
- If `uvx` fallback is used, upstream `github/spec-kit` is pinned to `v0.4.3` by default (override with `--spec-kit-ref`)
- `make` (POSIX) or PowerShell (Windows)

## Local development flow

1. Make changes in presets/extensions/scripts/docs.
2. If you changed Python dependencies, update both:
   - `extensions/itx-gates/requirements.txt` (runtime)
   - `requirements-dev.txt` (lint/type/security tooling)
   - Keep `pyproject.toml` in sync with pinned versions.
3. If you edited `preset.yml`, regenerate pattern indexes:
   - POSIX: `make build-pattern-index`
   - PowerShell: `.\scripts\tasks.ps1 -Task build-pattern-index`
4. Run validation:
   - POSIX:
     - `make compile`
     - `make test`
     - `make validate-catalog`
   - PowerShell:
     - `.\scripts\tasks.ps1 -Task compile`
     - `.\scripts\tasks.ps1 -Task test`
     - `.\scripts\tasks.ps1 -Task validate-catalog`
5. Optionally build artifacts:
   - POSIX: `make build-artifacts`
   - PowerShell: `.\scripts\tasks.ps1 -Task build-artifacts`

## Key files

- `presets/base/policy.yml` — shared gate enforcement rules (plan tiers, mandatory sections, placeholder markers). Consumed by `orchestrator.py` at runtime.
- `scripts/build_knowledge_manifest.py` — generates `knowledge-manifest.json` during bootstrap for structured hydration.
- `presets/*/pattern-index.md` — generated from `preset.yml` via `scripts/build_pattern_index.py`. Do not edit by hand; CI verifies they are up to date.

## Versioning and releases

Use semantic versioning (`X.Y.Z`).

- Bump versions everywhere using one command:
  - POSIX: `make release VERSION=0.2.0`
  - PowerShell: `.\scripts\tasks.ps1 -Task release -Version 0.2.0`
- Build release zips:
  - POSIX: `make build-artifacts`
  - PowerShell: `.\scripts\tasks.ps1 -Task build-artifacts`

Artifacts are produced in `dist/` and must match the version declared in `catalog/index.json`.

## Gate contract notes

- Both Tier 1 and Tier 2 findings are written to `.specify/context/gate_feedback.md`.
- Tier 1 failures return exit code `0`; Tier 2 failures return non-zero.
- Docker fallback currently verifies sandbox/container availability via `docker exec`; full in-container validator execution is future hardening work.

## Pull request checklist

- [ ] Tests pass locally.
- [ ] Catalog/manifests are version-consistent.
- [ ] `pattern-index.md` files regenerated if `preset.yml` changed.
- [ ] README/KB docs are updated if behavior changed.
- [ ] No host-executed fallback CLI paths were introduced.
- [ ] No floating branch refs were introduced for bootstrap extension installs.
