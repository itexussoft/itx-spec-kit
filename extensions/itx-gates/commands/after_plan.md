---
description: "Run itx-gates after_plan quality gates"
---

## Purpose

Execute the Itexus quality gates orchestrator for the `after_plan` lifecycle event.
Validates that a plan was produced during `/speckit.plan` and that its mandatory
sections are populated. When `.itx-config.yml` uses `knowledge.mode: lazy`, this
gate also resolves and materializes only the pattern files explicitly selected in
the plan (via `<!-- selected_patterns: ... -->` or inline filename references).

## How to execute

```bash
python .specify/extensions/itx-gates/hooks/orchestrator.py \
  --event after_plan \
  --workspace .
```

Gate enforcement rules (mandatory sections, placeholder markers) are defined in
`.specify/policy.yml`. See `docs/knowledge-base/workflow-and-gates.md` for the
full gate reference.
