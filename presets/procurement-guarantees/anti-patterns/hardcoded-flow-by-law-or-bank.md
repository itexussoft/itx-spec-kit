---
tags:
  - hardcode
  - flow
  - bank
  - law
  - procurement
anti_tags:
  - react
  - ui
  - component
  - theme
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Anti-Pattern: Hardcoded Flow by Law or Bank

> **Domain:** Procurement Guarantees
> **Severity:** MUST NOT — creates an unmaintainable matrix of local quirks inside the core domain.
> **Remedy:** Product templates, policy objects, provider strategies, and adapters.

---

## 1. Definition

This anti-pattern appears when one country's procurement law, one buyer's
document pack, or one issuer's transport quirks are encoded directly into core
services as permanent branches.

Examples:

- `if country == "RU":`
- `if bank_name == "X":`
- `if product_type == "bid-bond" and buyer == "Y":`

inside domain services that should stay generic.

---

## 2. Why It Is Forbidden

| Problem | Consequence |
|---------|-------------|
| Core services know local legal variants | Every new market duplicates the same lifecycle logic. |
| Provider quirks leak into domain logic | Switching or adding issuers becomes high-risk refactoring. |
| Product taxonomy is frozen in code | New guarantee types require service rewrites instead of template rollout. |

---

## 3. Common Violations

| Violation | Example |
|-----------|---------|
| Jurisdiction branch in core service | `if regulation == "44-FZ": required_docs = ...` |
| Bank-specific branch in aggregate | `if issuer_code == "BANK_A": expire_in = 30` |
| Product-specific status logic | `if product == "advance-payment": status = ...` inside generic lifecycle service |

---

## 4. Detection Checklist

- [ ] Domain or application services branch on jurisdiction, bank name, or buyer template.
- [ ] Provider DTO fields appear in core aggregate logic.
- [ ] New product onboarding requires editing core domain code instead of adding configuration or strategy.

---

## 5. Correct Alternative

- Product differences belong in `FlowDefinition` / `FlowVersion`.
- Provider differences belong in a capability `Strategy` or adapter.
- Claim, amendment, and release rules belong in policy objects.

---

## 6. AI Agent Enforcement Rules

1. **NEVER** encode country-specific law or issuer brand names in core domain branches.
2. **ALWAYS** prefer new templates, versions, policy objects, or adapter mappings.
3. When a user requests a new guarantee variant, first ask: new template, new provider capability, or new core behavior?
