# Patch Plan — [Feature / Change Title]

> **Prepared during:** `/speckit.plan` phase
> **Use when:** Change is scoped to existing modules with no new Bounded Contexts or Aggregates
> **Author:** [AI Agent / Human]
> **Date:** YYYY-MM-DD
> **Status:** [Draft | Approved | Superseded]

---

## 1. Problem Statement

_One short paragraph describing the issue or requested change._

## 2. Files / Modules Affected

_List impacted files, modules, or services and the expected scope of edits._

- _e.g., `src/service.py` — adjust validation rule_
- _e.g., `tests/test_service.py` — add regression test_

## 3. Patterns Applied (Optional)

_If any existing patterns from `.specify/patterns/` or `.specify/design-patterns/`
are relevant, list them. If not, write "N/A"._

_In lazy knowledge mode, use a structured selection block to materialize
needed files. Use `none` if no patterns are required:_

<!-- selected_patterns: none -->

| Pattern | File Reference | Why It Applies |
|---------|----------------|----------------|
| | | |

## 3b. Overlay Triggers (Optional)

_Use only when relevant. These are lightweight overlays, not new workflow commands._

- ACL trigger: if this patch touches third-party/legacy integrations, include `adapter-anti-corruption.md` in `selected_patterns`.
- Security micro-overlays: note if auth/secrets, OWASP trust-boundary, or rate-limiting checks are required.
- TDD trigger (modify path): when changing existing behavior, call out the failing regression/unit test you will write first.

## 4. Risks and Mitigations (Optional)

_Capture only concrete risks introduced by this patch-level change._

| Risk | Mitigation |
|------|------------|
| | |

## 5. Regression Testing

_At minimum, declare one regression test that covers the changed behavior path._

| Changed Behavior | Test Type | File |
|------------------|-----------|------|
| _e.g., Validation rule tightened_ | _E2E or integration_ | _e.g., `e2e_test_validation.py`_ |

---

_Template source: `presets/base/templates/patch-plan-template.md`_
