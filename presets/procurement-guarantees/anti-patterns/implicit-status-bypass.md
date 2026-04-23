---
tags:
  - status
  - lifecycle
  - bypass
  - transition
  - application
  - track
anti_tags:
  - react
  - ui
  - component
  - badge
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Anti-Pattern: Implicit Status Bypass

> **Domain:** Procurement Guarantees
> **Severity:** MUST NOT — destroys lifecycle determinism, evidence correctness, and claim semantics.
> **Remedy:** Explicit transition commands and guarded state machines.

---

## 1. Definition

**Implicit status bypass** means changing application or undertaking-track state
by direct assignment instead of using a transition boundary that validates
preconditions, permissions, and side effects.

Example:

```python
track.track_status = "ISSUED"
application.status = "APPROVED"
```

---

## 2. Why It Is Forbidden

| Problem | Consequence |
|---------|-------------|
| No precondition validation | Illegal jumps skip required documents, approvals, or claim checks. |
| No evidence emission | Status changes happen without history, snapshot, or audit records. |
| Broken aggregation | Parent application state no longer matches issuer-track reality. |
| Hidden side effects | Notifications, provider messages, or exposure changes are skipped. |

---

## 3. Common Violations

- Direct `.status = ...` or `.track_status = ...`
- Generic `setStatus(...)` mutator on aggregates
- SQL `UPDATE` against status fields from controller or script code
- Background job changing status without transition command

---

## 4. Detection Checklist

- [ ] Status field assignment appears outside a dedicated command handler or state machine.
- [ ] Controller changes status directly after validation.
- [ ] SQL script updates lifecycle state without emitting history.

---

## 5. Correct Alternative

- Use a command such as `ApproveIssuance`, `RegisterDemand`, `AcceptRelease`, or `ExpireUndertaking`.
- Validate source state, permissions, and required evidence inside the handler.
- Persist history and side effects from the same transition boundary.

---

## 6. AI Agent Enforcement Rules

1. **NEVER** assign status fields directly in controllers, services, or scripts.
2. **ALWAYS** route lifecycle changes through explicit transition handlers.
3. **ALWAYS** emit history and required side effects from the transition boundary.
