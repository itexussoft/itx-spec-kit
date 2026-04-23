# Architecture and Maintenance Guide

## Runtime responsibility boundaries

- `scripts/itx_init.py`: bootstrap entrypoint. Initializes workspace, installs presets/extensions, writes `.itx-config.yml`, and stages docs/knowledge.
- `scripts/itx_specify.py`: shared specify-cli constants and helpers (`specify init` argv, allowed integration keys for the pinned spec-kit tag, `spec_kit_ref` loading, pinned **`EXTENSION_REFS`** for community extensions, **`install_community_extensions`**, workflow **materialization** and **registry mirror** helpers for `--add-ai`). Used by `itx_init.py` and `patch.py`.
- `scripts/patch.py`: post-bootstrap updater. Applies kit updates to existing workspaces with safe handling for user-editable files. Optional **`--retarget-ai`** / **`--add-ai`** adjust Spec-Kit agent scaffolding while preserving Itexus-owned paths (retarget) or merging a second agent’s tree from a temp init (add); both require **specify** or **uvx** on `PATH`. After patch, both modes can re-run community extension install plus workflow/registry alignment for the target agent (unless **`--skip-add-ai-extension-sync`**).
- `extensions/itx-brownfield-workflows`: extension-provided brownfield intake command surface. Commands establish workstream metadata and hand off to `/speckit.plan`.
- `extensions/itx-gates/hooks/gatectl.py`: host-facing wrapper for `after_*` gate execution in hosts where hook firing is not guaranteed.
- `extensions/itx-gates/hooks/orchestrator.py`: core validator runtime invoked by `gatectl.py` (or by hook host integrations).
- `extensions/itx-gates/commands/run_speckit.py`: adapter for community extension command execution (`review.run`, `cleanup.run`) with local fallback prompt resolution.

## Current compatibility framing

- Upstream `spec-kit` core workflow commands remain the canonical base.
- Brownfield intake commands in this kit are local extension commands and are not guaranteed upstream core commands.
- `run_speckit.py` is intentionally limited to extension command dispatch (`review.run`, `cleanup.run`) and should not be used for core workflow slash commands.
- Legacy pseudo-command docs (`review_run.md`, `cleanup_run.md`) are intentionally not part of the supported command surface.

## Gate runtime artifacts

- `.itx-config.yml` stores `hook_mode` and informs whether host wrappers should ensure gate execution.
- `.specify/context/gate-state.yml` stores latest machine-readable gate state.
- `.specify/context/gate-events.jsonl` stores append-only gate execution history.
- `.specify/context/last-gate-summary.md` stores latest human-readable gate summary.
- `.specify/context/gate_feedback.md` stores Tier 1 and Tier 2 findings when present.

## Reproducibility policy

- Always pin upstream refs for community extensions in `scripts/itx_specify.py` (`EXTENSION_REFS`).
- Avoid branch-based refs (`main`, `master`) in bootstrap defaults.
- If bootstrap dependency refs change, update docs and run full local validation (`make compile`, `make test`, `make validate-catalog`).

## Dependency update policy

- Runtime dependencies are pinned in `extensions/itx-gates/requirements.txt`.
- Dev/CI tooling dependencies are pinned in `requirements-dev.txt`.
- Keep mirrored versions in `pyproject.toml` synchronized with both files.
- Bump dependency versions in isolated pull requests whenever possible.

## Security assurance controls

- CI must run secret scanning (`gitleaks`) and fail on verified leaks.
- CI must run dependency audit (`pip-audit`) on runtime and dev requirements.
- CI must enforce an allow-list license policy (`pip-licenses --allow-only ...`).
- Per release, verify these controls are still required checks on the default branch.

## Suggested maintenance cadence

- Weekly: review upstream extension/spec-kit releases and decide whether to bump pinned refs.
- Monthly: run dependency upgrades and security audit review.
- Per release: ensure docs and CI still reflect the current pinned refs/dependency sets.
