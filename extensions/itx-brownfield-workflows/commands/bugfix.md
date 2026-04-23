---
description: "Plan a bugfix workflow using the bugfix-report artifact"
---

## Purpose

Use this extension command when the current scope is a brownfield defect fix.
This command is delivered by `itx-brownfield-workflows` and is not an upstream
core workflow guarantee.

## Expected planning artifact

Create or update:

`specs/<active-feature>/bugfix-report.md`

Use the template at:

`.specify/templates/bugfix-report-template.md`

## Next steps

After preparing the bugfix report, continue through the standard sequence:
`/speckit.tasks` -> implement -> quality gates.
