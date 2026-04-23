---
tags:
  - fallback
  - api
  - manual
  - track
  - integration
anti_tags:
  - react
  - ui
  - component
  - dropdown
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Anti-Pattern: Silent API-to-MANUAL Fallback

> **Domain:** Procurement Guarantees
> **Severity:** MUST NOT — changes operational and legal responsibility without explicit approval.
> **Remedy:** Explicit mode-switch command with audit and operator intent.

---

## 1. Definition

This anti-pattern occurs when a failed API or network delivery automatically
changes an undertaking track to manual handling without an explicit transition,
approval, or audit marker.

---

## 2. Why It Is Forbidden

| Problem | Consequence |
|---------|-------------|
| Responsibility changes silently | Operators believe the provider received the package when it did not. |
| Evidence becomes ambiguous | No clear record of which channel actually governed the track. |
| Recovery is non-deterministic | Retries, notifications, and SLA monitoring lose meaning. |

---

## 3. Common Violations

- catch network error → `track_mode = "MANUAL"`
- retry exhaustion → fallback flag only, no transition event
- webhook timeout → UI starts showing manual workflow automatically

---

## 4. Detection Checklist

- [ ] Error path assigns `MANUAL` directly.
- [ ] API timeout branch changes delivery mode without approval command.
- [ ] Integration failure only updates UI hint but not an audited transition.

---

## 5. Correct Alternative

- Keep the track in an explicit failure or retry-needed state.
- Let an operator or policy engine issue a named “switch to manual” command.
- Audit who changed the channel, when, and why.

---

## 6. AI Agent Enforcement Rules

1. **NEVER** change delivery mode on a raw exception path.
2. **ALWAYS** model channel change as a first-class transition.
3. **ALWAYS** preserve the failed API attempt in history before any manual takeover.
