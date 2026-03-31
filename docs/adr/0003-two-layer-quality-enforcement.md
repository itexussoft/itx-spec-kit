# ADR 0003: Two-Layer Quality Enforcement

- Status: Accepted
- Date: 2026-03-26

## Context

AI-assisted delivery workflows need quality enforcement, but one mechanism does
not fit both design-time and runtime needs.

- Design-time shaping needs broad guidance such as constitutions, patterns, and
  anti-patterns to steer architectural choices.
- Runtime safety needs deterministic checks that can detect critical violations
  at workflow boundaries.

Encoding all guidance as executable validators would be brittle and expensive.
Relying only on passive guidance would leave critical violations undetected.

## Decision

Adopt a two-layer quality model:

1. Passive guidance layer:
   - Constitution files, pattern catalogs, anti-pattern catalogs, and plan
     templates shape agent reasoning during specify, plan, and implement phases.
2. Active validation layer:
   - Python gate validators in `itx-gates` run at gate events
     (`after_plan`, `after_tasks`, `after_implement`) and enforce targeted,
     high-signal checks only.

The passive layer is broad and advisory. The active layer is narrow and
enforced.

Gate findings may include rule metadata (confidence and remediation ownership)
to separate deterministic failures from heuristic advisories while preserving
deterministic workflow control.

## Consequences

- Positive:
  - Guidance content and validator code can evolve independently.
  - Validators remain focused and maintainable.
  - New domains can start with guidance and add validators incrementally for
    high-risk rules.
- Trade-offs:
  - Teams must understand that validator coverage is intentionally partial.
  - Coverage boundaries must stay visible in documentation through a maintained
    rule-to-control matrix (`enforced`, `advisory`, `planned`).

## Related Files

- `presets/base/constitution.md`
- `presets/base/docs/workflow-and-gates.md`
- `presets/base/patterns/`
- `presets/base/design-patterns/`
- `presets/base/anti-patterns/`
- `extensions/itx-gates/hooks/orchestrator.py`
- `extensions/itx-gates/hooks/validators/`
