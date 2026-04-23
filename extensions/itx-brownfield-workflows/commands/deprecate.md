---
description: "Initialize or update a brownfield deprecate workstream before /speckit.plan"
handoffs:
  - label: Create Plan
    agent: speckit.plan
    prompt: Use the active deprecate workstream metadata to create or update the correct planning artifact for this sunset slice
    send: true
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding.

## Purpose

Use this extension command as the intake entry point when phasing out existing
capability in a brownfield delivery slice. It establishes or updates the
active workstream metadata, then hands off to `/speckit.plan`, which creates
the `deprecate-plan.md` artifact for that slice.

It is shipped by the local `itx-brownfield-workflows` extension, not by
upstream core commands.

## When to use

Use `/speckit.deprecate` when:

- existing behavior or interface must be sunset over time
- compatibility window and consumer rollout need explicit treatment
- removal must be staged rather than immediate

Do **not** use this command for simple internal cleanup with no consumer impact;
use `/speckit.refactor` instead.

## Workstream conventions

- Default branch: `deprecate/<slug>`
- Default artifact root: `specs/deprecate-<slug>/`
- Keep the workstream dedicated to one sunset/migration path. Use
  `parent_feature` only when the deprecation is explicitly tied to a delivered
  feature lineage.

## Workflow state

Create or update `.specify/context/workflow-state.yml` before handing off to
`/speckit.plan`.

Minimum fields:

- `workstream_id`
- `work_class: deprecate`
- `artifact_root`
- `branch`
- `current_phase: plan`
- `phases.plan.status: in_progress`
- optional `parent_feature`

## Steps

1. Resolve the capability being sunset and confirm the rollout needs explicit
   compatibility-window management.
2. Choose a narrow workstream slug and branch/artifact-root convention for this
   deprecation path.
3. Update `.specify/context/workflow-state.yml` with the deprecate workstream
   metadata and ensure the artifact root exists.
4. Read only the minimum context needed to understand consumers, replacement
   path, rollout constraints, and verification expectations.
5. Summarize the workstream boundary, rollout posture, and any optional
   `parent_feature` linkage.
6. If there is no actual deprecation window or consumer impact, stop and choose
   a lighter workflow.

## Output

- updated `workflow-state.yml`
- chosen workstream id / branch / artifact root
- explicit rollout and compatibility-window summary

## Next steps

Continue with:

`/speckit.plan` -> `/speckit.tasks` -> `/speckit.implement` -> quality gates
