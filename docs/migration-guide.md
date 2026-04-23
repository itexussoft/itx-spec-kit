# Migration Guide

This guide explains how to adopt the current `itx-spec-kit` architecture without
reopening earlier wave semantics.

## Why this guide exists

Wave E2 productizes and clarifies architecture that already exists:

- brownfield intake commands route into `/speckit.plan`
- `itx-gates` host-facing execution uses `gatectl.py`
- `orchestrator.py` remains the validator runtime
- `run_speckit.py` remains the adapter for community `review.run` and `cleanup.run`

## Command ownership model

- Upstream core workflow commands:
  - `/speckit.constitution`
  - `/speckit.specify`
  - `/speckit.clarify`
  - `/speckit.plan`
  - `/speckit.tasks`
  - `/speckit.analyze`
  - `/speckit.implement`
- Local brownfield intake extension (`itx-brownfield-workflows`):
  - `/speckit.bugfix`
  - `/speckit.refactor`
  - `/speckit.modify`
  - `/speckit.hotfix`
  - `/speckit.deprecate`
- Local gate extension (`itx-gates`):
  - hook events: `after_plan`, `after_tasks`, `after_implement`, `after_review`
  - host-facing invocation: `gatectl.py ensure --event <event>`
  - extension command ids: `speckit.itx-gates.after-*`
- Community extension commands:
  - `review.run`
  - `cleanup.run`
  - execute via `run_speckit.py`

Brownfield intake commands are extension-provided and are not guaranteed upstream core commands.

## Runtime model and persisted state

- `.itx-config.yml` keeps `hook_mode` (`auto`, `hybrid`, `manual`) so hosts know
  whether to rely on auto hooks or call wrappers directly.
- `gatectl.py` is the host-facing wrapper and should be used for manual/hybrid
  ensure flow.
- `orchestrator.py` performs the core validations and writes gate outputs:
  - `.specify/context/gate-state.yml`
  - `.specify/context/gate-events.jsonl`
  - `.specify/context/last-gate-summary.md`

## Old-to-new mapping

- `system-design-plan.md` maps to `feature` work class behavior.
- `patch-plan.md` maps to `patch` work class behavior.
- Existing feature/patch projects can continue without forced structural migration.
- Legacy compatibility artifacts may still use `plan_tier` wording; treat that as
  compatibility vocabulary while `work_class` remains the preferred framing.
- For new brownfield slices, start with the matching intake command and then run
  `/speckit.plan`:
  - bugfix -> `bugfix-report.md`
  - refactor -> `refactor-plan.md`
  - modify -> `modify-plan.md`
  - hotfix -> `hotfix-report.md`
  - deprecate -> `deprecate-plan.md`

## Incremental adoption path

1. Keep existing artifacts and workflow intact.
2. Update workspace kit files with `scripts/patch.py`.
3. Use brownfield intake commands only for new brownfield slices.
4. Continue using `/speckit.plan` as the planning entry after intake.
5. Use `run_speckit.py` for community review/cleanup and `gatectl.py ensure` where host hooks are not guaranteed.

## Removed pseudo-command note

Legacy pseudo-command docs such as `review_run.md` and `cleanup_run.md` are not
part of the supported command surface.
