# Architecture and Maintenance Guide

## Runtime responsibility boundaries

- `scripts/itx_init.py`: bootstrap entrypoint. Initializes workspace, installs presets/extensions, writes `.itx-config.yml`, and stages docs/knowledge.
- `scripts/patch.py`: post-bootstrap updater. Applies kit updates to existing workspaces with safe handling for user-editable files.
- `extensions/itx-gates/hooks/orchestrator.py`: runtime gate controller. Executes plan/implement validations and writes gate feedback artifacts.

## Reproducibility policy

- Always pin upstream refs for community extensions in `scripts/itx_init.py` (`EXTENSION_REFS`).
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
