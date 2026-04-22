# Test Strategy — [Feature / Project]

> **Prepared during:** `/speckit.plan` or before `/speckit.implement`
> **Author:** [AI Agent / Human]
> **Date:** YYYY-MM-DD
> **Status:** [Draft | Approved | Superseded]

---

## 1. Test Scope and Objectives

- In-scope capabilities:
- Out-of-scope capabilities:
- Key quality objectives:

## 2. Test Pyramid and Coverage Targets

| Level | Goal | Coverage / Target | Notes |
|------|------|-------------------|-------|
| Unit | Fast domain correctness | | |
| Integration | Boundary correctness | | |
| End-to-End | User journey confidence | | |

## 3. End-to-End Test Scenarios

| User Journey / Flow | Entry Point | Key Assertions | Data Setup |
|---------------------|-------------|----------------|------------|
| | | | |

## 4. Integration Test Boundaries

| Boundary | What Is Verified | Test Double Strategy |
|----------|------------------|----------------------|
| | | |

## 4b. TDD and Regression Loop

- For `bugfix` and `refactor` work classes, define the initial failing unit/regression test slice before production edits.
- For modify-style patch changes, prefer the same red-green-refactor loop when business behavior changes.
- Keep this additive to existing E2E/integration requirements; do not replace them.

## 5. Test Environment

- Runtime/services required:
- Container strategy:
- External dependencies and stubs:

## 6. Test Data Management

- Fixture/factory strategy:
- Seeding/reset strategy:
- Deterministic time/ID handling:

## 7. CI Integration

- Pipeline stage placement:
- Parallelism/sharding:
- Timeout and retry policy:
- Failure diagnostics and artifacts:

---

_Template source: `presets/base/templates/test-strategy-template.md`_
