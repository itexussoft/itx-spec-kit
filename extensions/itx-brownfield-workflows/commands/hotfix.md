---
description: "Initialize or update an urgent brownfield hotfix workstream before /speckit.plan"
handoffs:
  - label: Create Plan
    agent: speckit.plan
    prompt: Use the active hotfix workstream metadata to create or update the correct planning artifact for this incident slice
    send: true
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding.

## Purpose

Use this extension command as the intake entry point for urgent brownfield
corrections linked to an incident. It establishes or updates the active
workstream metadata, then hands off to `/speckit.plan`, which creates the
`hotfix-report.md` artifact for that slice.

This command is extension-provided by `itx-brownfield-workflows` and is not an
upstream core guarantee.

## When to use

Use `/speckit.hotfix` when:

- an incident or severe production risk needs immediate correction
- scope must stay minimal and reversible
- incident linkage and verification are required

Do **not** use this command for routine bugfixes without incident pressure; use
`/speckit.bugfix` instead.

## Workstream conventions

- Default branch: `hotfix/<slug>`
- Default artifact root: `specs/hotfix-<slug>/`
- Keep the slice minimal, incident-linked, and independently revertible. Use
  `parent_feature` only when it helps tie the incident to a delivered feature.

## Workflow state

Create or update `.specify/context/workflow-state.yml` before handing off to
`/speckit.plan`.

Minimum fields:

- `workstream_id`
- `work_class: hotfix`
- `artifact_root`
- `branch`
- `current_phase: plan`
- `phases.plan.status: in_progress`
- optional `parent_feature`

## Steps

1. Resolve the incident-linked slice and confirm the urgency warrants a hotfix
   path rather than a normal bugfix.
2. Choose a narrow workstream slug and branch/artifact-root convention for this
   incident correction.
3. Update `.specify/context/workflow-state.yml` with the hotfix workstream
   metadata and ensure the artifact root exists.
4. Read only the minimum context required to restore service safely and define
   the incident-linked regression target.
5. Summarize the workstream boundary, rollback posture, and any optional
   `parent_feature` linkage.
6. If urgency is not real, stop and downgrade to `/speckit.bugfix`.

## Output

- updated `workflow-state.yml`
- chosen workstream id / branch / artifact root
- short summary of safe scope, rollback posture, and verification target

## Next steps

Continue with:

`/speckit.plan` -> `/speckit.tasks` -> `/speckit.implement` -> quality gates
