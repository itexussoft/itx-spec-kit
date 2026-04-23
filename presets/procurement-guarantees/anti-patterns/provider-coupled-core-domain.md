---
tags:
  - provider
  - dto
  - swift
  - coupling
  - adapter
anti_tags:
  - react
  - ui
  - component
  - form
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Anti-Pattern: Provider-Coupled Core Domain

> **Domain:** Procurement Guarantees
> **Severity:** MUST NOT — makes the platform hostage to one transport or provider schema.
> **Remedy:** Anti-corruption adapters and stable internal models.

---

## 1. Definition

This anti-pattern appears when SWIFT tags, insurer payload fields, surety
provider DTOs, or bank-specific enums are treated as core domain concepts.

Examples:

- domain object field named `mt760_77c`
- aggregate method that switches on provider payload codes
- internal status equal to an external provider enum by design

---

## 2. Why It Is Forbidden

| Problem | Consequence |
|---------|-------------|
| Core model depends on one provider schema | Replacing or adding providers requires core refactor. |
| Transport and business semantics are conflated | Issuance, amendment, and demand become tied to message format. |
| Tests become provider-fixture-driven | Internal invariants are hidden behind external payload shape. |

---

## 3. Detection Checklist

- [ ] Core entities expose provider DTO fields directly.
- [ ] Domain logic branches on SWIFT tag names or provider payload keys.
- [ ] Repository or service interfaces return raw provider payloads as domain objects.

---

## 4. Correct Alternative

- Keep external formats inside adapters or facades.
- Map them to stable internal concepts: undertaking, amendment, presentation, release.
- Treat transport schemas as boundary concerns, not core domain vocabulary.

---

## 5. AI Agent Enforcement Rules

1. **NEVER** let provider DTOs or SWIFT tags leak past the adapter boundary.
2. **ALWAYS** map external payloads to internal commands or value objects.
3. **ALWAYS** keep provider-specific translation code stateless and isolated.
