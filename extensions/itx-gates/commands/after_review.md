---
description: "Run itx-gates after_review quality gates"
scripts:
  sh: hooks/gatectl.py ensure --event after_review --workspace .
---

## Purpose

Ensure the Itexus quality gates orchestrator has executed for the `after_review` lifecycle
event. Verifies completion readiness: all tasks checked, no outstanding Tier 2
findings in gate feedback, and presence of assertion-bearing E2E tests.

## When to run

- immediately after review completion (`/speckit.review.run` or equivalent)
- again after resolving review findings or other delivery blockers

## How to execute

```bash
python {SCRIPT}
```

The wrapper is host-aware:

- if the gate state is stale or missing, it runs `orchestrator.py`
- if the gate is already fresh, it skips rerunning and preserves the last result

## How to interpret the result

- Exit `0` and no `.specify/context/gate_feedback.md`: the gate passed cleanly.
- Exit `0` and `gate_feedback.md` exists: Tier 1 findings were recorded for
  auto-correction; fix them and rerun `after_review`.
- Exit `1`: Tier 2 findings were recorded; stop and escalate to human review.

## Artifacts

- `.specify/context/gate_feedback.md` when findings exist
- `.specify/context/execution-brief.md` refreshed after the gate run
- `.specify/context/gate-state.yml` with the latest machine-readable gate state
- `.specify/context/gate-events.jsonl` with append-only gate execution events
- `.specify/context/last-gate-summary.md` with the latest human-readable summary

See `docs/knowledge-base/workflow-and-gates.md` for the full gate reference.
