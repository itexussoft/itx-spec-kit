---
tags:
  - policy
  - claim
  - presentation
  - examination
  - guarantee
anti_tags:
  - react
  - ui
  - component
  - table
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Policy Object: Presentation Examination

> **Domain:** Procurement Guarantees
> **Phase relevance:** Tasks, Implement

---

## 1. Intent

Model claim and demand examination as a **Policy Object** so the required
evidence, validation rules, and rejection reasons live in a reusable,
testable unit instead of controller conditionals.

---

## 2. Structure

```python
class PresentationExaminationPolicy(Protocol):
    def examine(self, package: PresentationPackage) -> ExaminationResult: ...

class UrdgDemandPolicy:
    ...

class BidBondClaimPolicy:
    ...
```

The handler chooses the right policy by product template and provider
capability, then executes it against the immutable presentation package.

---

## 3. Why It Helps

- separates transport from business examination
- supports product-specific claim rules
- returns structured non-compliance reasons
- keeps claim logic unit-testable without API fixtures

---

## 4. AI Agent Directives

1. Use policy objects when claim or examination rules vary by product or issuer.
2. Keep policy outputs structured: `complying`, `reasons`, `missing_docs`, `next_action`.
3. Do not bury document-requirement logic inside web controllers.
