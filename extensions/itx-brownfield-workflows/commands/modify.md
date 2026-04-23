---
description: "Initialize or update a brownfield modify workstream before /speckit.plan"
handoffs:
  - label: Create Plan
    agent: speckit.plan
    prompt: Use the active modify workstream metadata to create or update the correct planning artifact for this behavior-change slice
    send: true
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding.

## Purpose

Use this extension command as the intake entry point when changing existing
behavior inside brownfield scope. It establishes or updates the active
workstream metadata, then hands off to `/speckit.plan`, which creates the
`modify-plan.md` artifact for that slice.

It is provided by `itx-brownfield-workflows`, not by upstream core workflow
commands.

## When to use

Use `/speckit.modify` when:

- existing capability must behave differently
- compatibility and downstream impact need explicit handling
- the change is not large enough to justify a brand-new feature spec

Do **not** use this command for pure defect correction; use `/speckit.bugfix`.
Do **not** use it for behavior-preserving cleanup; use `/speckit.refactor`.

## Workstream conventions

- Default branch: `modify/<slug>`
- Default artifact root: `specs/modify-<slug>/`
- If the change is tightly bound to an already delivered feature, prefer:
  - branch `modify/<parent-feature>-<slug>`
  - artifact root `specs/<parent-feature>/modifications/<slug>/`
  - `parent_feature: <parent-feature>`

## Workflow state

Create or update `.specify/context/workflow-state.yml` before handing off to
`/speckit.plan`.

Minimum fields:

- `workstream_id`
- `work_class: modify`
- `artifact_root`
- `branch`
- `current_phase: plan`
- `phases.plan.status: in_progress`
- optional `parent_feature`

## Steps

1. Resolve the behavior-change slice and decide whether it belongs to a parent
   delivered feature or should live as its own workstream.
2. Choose the branch and artifact-root convention that best matches that
   ownership.
3. Update `.specify/context/workflow-state.yml` with the modify workstream
   metadata and ensure the artifact root exists.
4. Read only the context needed to understand current behavior, target
   behavior, compatibility impact, and regression expectations.
5. Keep traceability explicit for the changed behavior and summarize any
   `parent_feature` linkage.
6. If the change is actually a new capability, stop and use `/speckit.specify`.

## Output

- updated `workflow-state.yml`
- chosen workstream id / branch / artifact root
- short summary of changed behavior, compatibility risk, and regression target

## Next steps

Continue with:

`/speckit.plan` -> `/speckit.tasks` -> `/speckit.implement` -> quality gates
