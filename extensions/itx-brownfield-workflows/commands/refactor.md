---
description: "Initialize or update a brownfield refactor workstream before /speckit.plan"
handoffs:
  - label: Create Plan
    agent: speckit.plan
    prompt: Use the active refactor workstream metadata to create or update the correct planning artifact for this slice
    send: true
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding.

## Purpose

Use this extension command as the intake entry point for behavior-preserving
brownfield refactor work. It establishes or updates the active workstream
metadata, then hands off to `/speckit.plan`, which creates the
`refactor-plan.md` artifact for that slice.

This command is provided by the local `itx-brownfield-workflows` extension and
should not be treated as an upstream core command.

## When to use

Use `/speckit.refactor` when:

- structure must improve without changing intended behavior
- invariants and validation strategy can be stated explicitly
- the slice is technical rather than product-functional

Do **not** use this command for behavior changes; use `/speckit.modify`
instead. Do **not** use it for net-new capability; use `/speckit.specify`.

## Workstream conventions

- Default branch: `refactor/<slug>`
- Default artifact root: `specs/refactor-<slug>/`
- If the refactor is tightly scoped to an already delivered feature, keep that
  feature in `parent_feature` and still use a dedicated workstream root unless
  a nested brownfield directory is clearly better for the repo.

## Workflow state

Create or update `.specify/context/workflow-state.yml` before handing off to
`/speckit.plan`.

Minimum fields:

- `workstream_id`
- `work_class: refactor`
- `artifact_root`
- `branch`
- `current_phase: plan`
- `phases.plan.status: in_progress`
- optional `parent_feature`

## Steps

1. Resolve the technical slice being refactored and confirm it is
   behavior-preserving.
2. Choose a narrow workstream slug and branch/artifact-root convention for this
   slice.
3. Update `.specify/context/workflow-state.yml` with the refactor workstream
   metadata and ensure the artifact root exists.
4. Read only the context needed to understand preserved behavior, invariants,
   and regression expectations.
5. Summarize the planned workstream boundary, preserved behavior, and any
   optional `parent_feature` linkage.
6. If behavior must change, stop and redirect to `/speckit.modify`.

## Output

- updated `workflow-state.yml`
- chosen workstream id / branch / artifact root
- short summary of preserved invariants and regression boundary

## Next steps

Continue with:

`/speckit.plan` -> `/speckit.tasks` -> `/speckit.implement` -> quality gates
