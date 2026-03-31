---
description: "Run itx-gates after_implement quality gates"
---

## Purpose

Execute the Itexus quality gates orchestrator for the `after_implement` lifecycle
event. Runs domain-specific validators (trading AST, banking heuristic, healthcare
regex) in addition to the standard checks.

## How to execute

```bash
python .specify/extensions/itx-gates/hooks/orchestrator.py \
  --event after_implement \
  --workspace .
```

See `docs/knowledge-base/workflow-and-gates.md` for the full gate reference.
