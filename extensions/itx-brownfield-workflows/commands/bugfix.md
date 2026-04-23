---
description: "Initialize or update a brownfield bugfix workstream before /speckit.plan"
handoffs:
  - label: Create Plan
    agent: speckit.plan
    prompt: Use the active bugfix workstream metadata to create or update the correct planning artifact for this defect slice
    send: true
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding.

## Purpose

Use this extension command as the intake entry point for a brownfield bugfix
slice. It establishes or updates the active workstream metadata, then hands
off to `/speckit.plan`, which creates the `bugfix-report.md` artifact for that
slice.

This command is delivered by `itx-brownfield-workflows` and is not an upstream
core workflow guarantee.

## When to use

Use `/speckit.bugfix` when:

- existing behavior is wrong and must be corrected
- reproduction is known or can be narrowed to a concrete failing path
- the fix should preserve intended behavior everywhere else

Do **not** use this command for new capability. Use `/speckit.specify` for new
feature work. Do **not** use this command when the target outcome is a
behavior-preserving structural cleanup; use `/speckit.refactor` instead.

## Workstream conventions

- Default branch: `bugfix/<slug>`
- Default artifact root: `specs/bugfix-<slug>/`
- Keep the slice tightly scoped to the failing path. Use `parent_feature` only
  when the defect clearly belongs to a known delivered feature or release unit.

## Workflow state

Create or update `.specify/context/workflow-state.yml` before handing off to
`/speckit.plan`.

Minimum fields:

- `workstream_id`
- `work_class: bugfix`
- `artifact_root`
- `branch`
- `current_phase: plan`
- `phases.plan.status: in_progress`
- optional `parent_feature`

## Steps

1. Resolve the failing slice and confirm the work is defect correction rather
   than a new capability or deliberate behavior change.
2. Choose a narrow workstream slug and branch/artifact-root convention for this
   defect.
3. Update `.specify/context/workflow-state.yml` with the bugfix workstream
   metadata and ensure the artifact root exists.
4. Read only the minimum context needed to preserve intended behavior and
   define the regression target.
5. Summarize the planned workstream boundary, affected path, and any optional
   `parent_feature` linkage.
6. If the defect cannot be scoped cleanly, stop and ask for a narrower target.

## Output

- updated `workflow-state.yml`
- chosen workstream id / branch / artifact root
- short summary of scope, affected behavior, and regression target

## Next steps

Continue with:

`/speckit.plan` -> `/speckit.tasks` -> `/speckit.implement` -> quality gates
