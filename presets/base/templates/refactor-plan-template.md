---
work_class: refactor
---

# Refactor Plan — [Change Title]

> **Prepared during:** `/speckit.plan` phase
> **Use when:** Technical refactor that preserves behavior while improving structure
> **Author:** [AI Agent / Human]
> **Date:** YYYY-MM-DD
> **Status:** [Draft | Approved | Superseded]

---

## 1. Goal

_State the technical objective of this refactor in one short paragraph._

## 2. Scope / Non-Scope

_Declare what is included and what is explicitly excluded in this refactor slice._

## 3. Invariants to Preserve

_List behavioral and technical invariants that must not change._

- _e.g., public API responses stay backward compatible_
- _e.g., persisted data model and migration state remain unchanged_

## 4. Public Contract Impact

_Document any external contract impact. If none, write `None` and explain why._

## 5. Behavioral Equivalence Strategy

_Describe how equivalence will be validated before and after refactor (baseline comparison, snapshots, golden tests, etc.)._

## 6. Regression Strategy

_List required regression coverage for changed paths._

| Changed Area | Test Type | File |
|--------------|-----------|------|
| | | |

## 6b. Overlay Triggers (Optional)

_Use only when relevant. Keep this lightweight and additive to existing flow._

- ACL trigger: if refactor crosses vendor/legacy boundaries, keep mappings and transport concerns inside adapters (`adapter-anti-corruption.md`).
- Security micro-overlays: call out auth/secrets, OWASP boundary checks, and rate-limiting concerns when refactor touches exposed interfaces.
- TDD rule: for behavior-adjacent refactor slices, preserve a red-green-refactor loop with focused failing tests before structural edits.

---

_Template source: `presets/base/templates/refactor-plan-template.md`_
