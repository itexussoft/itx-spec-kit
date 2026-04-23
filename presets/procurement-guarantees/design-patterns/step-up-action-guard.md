---
tags:
  - mfa
  - step-up
  - authorization
  - security
  - action-guard
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

# Guard: Step-Up Authorization

> **Domain:** Procurement Guarantees
> **Phase relevance:** Tasks, Implement

---

## 1. Intent

Use a dedicated **Guard** object for high-risk actions that require stronger
authorization than the base session.

Typical actions:

- issuance approval
- offer acceptance
- release authorization
- sensitive consent change

---

## 2. Structure

```python
class StepUpActionGuard:
    def assert_allowed(self, actor: ActorContext, action: SensitiveAction, proof: StepUpProof) -> None:
        ...
```

The guard is called before the command handler executes irreversible or
legally significant actions.

---

## 3. Why It Helps

- keeps MFA logic out of business handlers
- centralizes TTL, scope, and proof validation
- supports action-scoped elevation instead of blanket admin bypass

---

## 4. AI Agent Directives

1. Use an explicit guard for elevated actions.
2. Keep step-up proof short-lived and action-scoped.
3. Never bypass the guard for privileged roles without an explicit policy reason.
