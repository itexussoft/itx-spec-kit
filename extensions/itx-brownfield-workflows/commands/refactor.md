---
description: "Plan a refactor workflow using the refactor-plan artifact"
---

## Purpose

Use this extension command for behavior-preserving brownfield refactor work.
This command is provided by the local `itx-brownfield-workflows` extension and
should not be treated as an upstream core command.

## Expected planning artifact

Create or update:

`specs/<active-feature>/refactor-plan.md`

Use the template at:

`.specify/templates/refactor-plan-template.md`

## Next steps

Run the normal workflow after planning:
`/speckit.tasks` -> implement -> quality gates.
