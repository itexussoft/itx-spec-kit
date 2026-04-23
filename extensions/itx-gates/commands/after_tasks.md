---
description: "Run itx-gates after_tasks quality gates"
scripts:
  sh: hooks/gatectl.py ensure --event after_tasks --workspace .
---

## Purpose

Ensure the Itexus quality gates orchestrator has executed for the `after_tasks` lifecycle event.
Validates tasks file presence across supported locations and checks checkbox format expectations.

## When to run

- immediately after `/speckit.tasks`
- again after any corrective edits to `tasks.md`

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
  auto-correction; fix them and rerun `after_tasks`.
- Exit `1`: Tier 2 findings were recorded; stop and escalate to human review.

## Artifacts

- `.specify/context/gate_feedback.md` when findings exist
- `.specify/context/execution-brief.md` refreshed after the gate run
- `.specify/context/gate-state.yml` with the latest machine-readable gate state
- `.specify/context/gate-events.jsonl` with append-only gate execution events
- `.specify/context/last-gate-summary.md` with the latest human-readable summary

See `docs/knowledge-base/workflow-and-gates.md` for the full gate reference.
