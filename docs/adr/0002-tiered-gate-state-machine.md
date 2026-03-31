# ADR 0002: Tiered Gate State Machine

- Status: Accepted
- Date: 2026-03-25

## Context

Quality gates must enforce compliance-critical boundaries while still allowing autonomous correction for non-critical issues. A single failure mode (always fail hard or always continue) either blocks productivity or risks unsafe loops.

## Decision

Adopt a two-tier gate state machine:

1. Tier 1 (auto-correction):
   - For reversible, non-critical issues.
   - Write feedback to `.specify/context/gate_feedback.md`.
   - Exit `0` so the agent can iterate.
2. Tier 2 (hard halt):
   - For critical domain violations.
   - Write failure details to `stderr`.
   - Exit non-zero (`1`) to stop autonomous progression.

## Consequences

- Positive:
  - Preserves agent velocity for routine issues.
  - Enforces human-in-the-loop control for high-risk violations.
  - Improves traceability of non-critical remediation context.
- Trade-offs:
  - Requires clear rule severity classification.
  - Misclassification can over-halt or under-protect flows.

## Related Files

- `extensions/itx-gates/hooks/orchestrator.py`
- `extensions/itx-gates/hooks/validators/trading_ast.py`
- `extensions/itx-gates/hooks/validators/banking_heuristic.py`
- `extensions/itx-gates/hooks/validators/health_regex.py`
- `tests/test_orchestrator.py`
