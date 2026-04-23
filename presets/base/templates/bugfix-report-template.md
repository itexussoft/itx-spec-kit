---
work_class: bugfix
---

# Bugfix Report — [Issue Title]

> **Prepared during:** `/speckit.plan` phase
> **Use when:** Scoped defect correction with explicit reproduction and regression target
> **Author:** [AI Agent / Human]
> **Date:** YYYY-MM-DD
> **Status:** [Draft | Approved | Superseded]

---

## 1. Symptom

_Describe the observed failure, including user/system impact._

## 2. Reproduction

_Provide deterministic reproduction steps and environment context._

1. _Step one_
2. _Step two_
3. _Observed result_

## 3. Expected Behavior

_State the expected correct behavior for the same flow._

## 4. Regression Test Target

_Name the concrete regression test(s) that will prevent recurrence._

| Behavior Path | Test Type | File |
|---------------|-----------|------|
| | | |

## 5. Root Cause

_Summarize the technical root cause and affected code path._

## 6. Fix Strategy

_Describe the minimal correction approach and why it is safe._

## 6b. Overlay Triggers (Optional)

_Use only when relevant to this bugfix._

- ACL trigger: if defect is at a third-party/legacy boundary, keep vendor models/errors isolated behind adapters.
- Security micro-overlays: include auth/secrets, OWASP, or rate-limiting checks when the defect touches trust boundaries.
- TDD rule: start with a failing regression/unit test for the reproduced defect before implementing the fix.

## 6c. Gate Auto-Retry Evidence (Optional)

_Use when `after_implement` triggered auto-correction loops._

- Latest report: `.specify/context/gate-failure-report.md`
- Attempt trail: capture attempt count and resolved rule IDs from the report/audit log
- Final state: `[resolved in auto-retry | escalated to human review]`

---

_Template source: `presets/base/templates/bugfix-report-template.md`_
