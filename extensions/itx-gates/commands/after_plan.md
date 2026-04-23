---
description: "Run itx-gates after_plan quality gates"
scripts:
  sh: hooks/gatectl.py ensure --event after_plan --workspace .
---

## Purpose

Ensure the Itexus quality gates orchestrator has executed for the `after_plan` lifecycle event.
Validates that a plan was produced during `/speckit.plan` and that its mandatory
sections are populated. When `.itx-config.yml` uses `knowledge.mode: lazy`, this
gate also resolves and materializes only the pattern files explicitly selected in
the plan (via `<!-- selected_patterns: ... -->` or inline filename references).

## When to run

- immediately after `/speckit.plan`
- again after any corrective edits to the plan

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
  auto-correction; inspect the feedback, fix the issues, and rerun
  `after_plan`.
- Exit `1`: Tier 2 findings were recorded; stop and surface the findings for
  explicit human review.

## Artifacts

- `.specify/context/gate_feedback.md` when findings exist
- `.specify/context/execution-brief.md` refreshed after the gate run
- `.specify/context/audit-log.md` only when high-risk pre-action logging is triggered
- `.specify/context/gate-state.yml` with the latest machine-readable gate state
- `.specify/context/gate-events.jsonl` with append-only gate execution events
- `.specify/context/last-gate-summary.md` with the latest human-readable summary

Gate enforcement rules (mandatory sections, placeholder markers) are defined in
`.specify/policy.yml`. See `docs/knowledge-base/workflow-and-gates.md` for the
full gate reference.
