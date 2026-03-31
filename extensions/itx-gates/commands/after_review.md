---
description: "Run itx-gates after_review quality gates"
---

## Purpose

Execute the Itexus quality gates orchestrator for the `after_review` lifecycle
event. Verifies completion readiness: all tasks checked, no outstanding Tier 2
findings in gate feedback, and presence of assertion-bearing E2E tests.

## How to execute

```bash
python .specify/extensions/itx-gates/hooks/orchestrator.py \
  --event after_review \
  --workspace .
```

See `docs/knowledge-base/workflow-and-gates.md` for the full gate reference.
