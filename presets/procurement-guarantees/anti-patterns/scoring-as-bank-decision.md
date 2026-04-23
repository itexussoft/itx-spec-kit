---
tags:
  - scoring
  - decision
  - offer
  - bank
  - procurement
anti_tags:
  - react
  - ui
  - component
  - chart
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Anti-Pattern: Scoring as Issuance Decision

> **Domain:** Procurement Guarantees
> **Severity:** MUST NOT — conflates underwriting support with the legally operative undertaking.
> **Remedy:** Separate recommendation models from issuance and claim decisions.

---

## 1. Definition

This anti-pattern occurs when platform scoring, recommendation, or underwriting
output is stored or presented as if it were:

- an approved issuer decision
- an issued guarantee
- a complying claim decision
- an accepted offer

---

## 2. Why It Is Forbidden

| Problem | Consequence |
|---------|-------------|
| Forecast is mistaken for commitment | Users assume legal protection exists when it does not. |
| Competing issuer logic collapses | Internal recommendation can override provider reality. |
| Audit trail is corrupted | No clear line between platform advice and external undertaking. |

---

## 3. Common Violations

- `application.status = "ISSUED"` after internal score threshold
- UI label “approved guarantee” based only on platform recommendation
- exposure booked before provider issuance actually happens

---

## 4. Detection Checklist

- [ ] Scoring result directly changes issuance or offer status.
- [ ] Recommendation fields are reused as legal decision fields.
- [ ] UI wording treats recommendation as issued instrument.

---

## 5. Correct Alternative

- Keep scoring outputs in recommendation or underwriting read models.
- Move to issued/approved only after explicit provider or guarantor action.
- Keep legal undertaking evidence separate from scoring evidence.

---

## 6. AI Agent Enforcement Rules

1. **NEVER** equate score outcome with issued undertaking.
2. **NEVER** drive claim payment or release decisions from recommendation scores alone.
3. **ALWAYS** separate recommendation evidence from legal commitment evidence.
