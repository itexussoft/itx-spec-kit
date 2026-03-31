---
description: "Run itx-gates after_tasks quality gates"
---

## Purpose

Execute the Itexus quality gates orchestrator for the `after_tasks` lifecycle event.
Validates tasks file presence across supported locations and checks checkbox format expectations.

## How to execute

```bash
python .specify/extensions/itx-gates/hooks/orchestrator.py \
  --event after_tasks \
  --workspace .
```

See `docs/knowledge-base/workflow-and-gates.md` for the full gate reference.
