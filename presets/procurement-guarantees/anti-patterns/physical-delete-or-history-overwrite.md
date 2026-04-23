---
tags:
  - delete
  - history
  - snapshot
  - version
  - append-only
anti_tags:
  - react
  - ui
  - component
  - toast
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Anti-Pattern: Physical Delete or History Overwrite

> **Domain:** Procurement Guarantees
> **Severity:** MUST NOT — destroys forensic traceability for issuance, amendment, demand, and release.
> **Remedy:** Append-only history, new versions, and compensating records.

---

## 1. Definition

This anti-pattern occurs when snapshot rows, document versions, status history,
or claim evidence are deleted or overwritten instead of superseded by a new
version or compensating record.

---

## 2. Why It Is Forbidden

| Problem | Consequence |
|---------|-------------|
| Lost issuance trail | You cannot prove what undertaking text or document pack was used. |
| Lost claim evidence | Claim examination becomes irreproducible. |
| Broken audit | Release, expiry, and amendment actions cannot be reconstructed. |
| Exposure mismatch | Outstanding guarantee state can no longer be rebuilt safely. |

---

## 3. Common Violations

| Violation | Example |
|-----------|---------|
| Delete snapshot rows | `DELETE FROM track_field_snapshot ...` |
| Overwrite document version | `UPDATE document_version SET ...` |
| Reuse same record for amendment | “edit issued guarantee text in place” |
| Purge old claim package after resubmission | current claim survives, original claim disappears |

---

## 4. Detection Checklist

- [ ] `DELETE` or destructive `UPDATE` on snapshot, version, or history tables
- [ ] Document amendment modifies the original issued document row
- [ ] Claim resubmission overwrites the first presentation instead of creating a new one

---

## 5. Correct Alternative

- Create a new snapshot or document version.
- Record compensating events instead of destructive rewrite.
- Keep original presentation and examination artifacts immutable.

---

## 6. AI Agent Enforcement Rules

1. **NEVER** delete runtime history, snapshots, or document versions.
2. **NEVER** overwrite issued undertaking text in place.
3. **ALWAYS** represent amendment, claim resubmission, and release as new evidence records.
