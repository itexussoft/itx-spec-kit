---
tags:
  - decorator
  - document
  - signature
  - evidence
  - audit
anti_tags:
  - react
  - ui
  - component
  - upload
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Decorator: Document Evidence Pipeline

> **Domain:** Procurement Guarantees
> **Phase relevance:** Tasks, Implement
> **Extends:** `../../base/design-patterns/decorator-middleware.md`

---

## 1. Intent

Wrap document mutations in a composable pipeline so every upload, amendment,
signature, claim package, or release artifact receives the same cross-cutting
behavior without bloating handlers.

---

## 2. Structure

```
DocumentCommandHandler
  └── AuditDecorator
      └── ClassificationDecorator
          └── VersioningDecorator
              └── SignatureVerificationDecorator
                  └── SnapshotBindingDecorator
                      └── CoreHandler
```

Each decorator adds one concern and passes a richer command context
downstream.

---

## 3. When to Use

- upload of issuance documents
- amendment package handling
- claim or presentation package assembly
- release or discharge evidence capture

Do not use a decorator chain for pure read-only rendering paths.

---

## 4. Responsibilities by Decorator

| Decorator | Responsibility |
|-----------|----------------|
| `AuditDecorator` | Record actor, action, target, and correlation id |
| `ClassificationDecorator` | Resolve document type and lifecycle role |
| `VersioningDecorator` | Create new version or new document intentionally |
| `SignatureVerificationDecorator` | Validate signature and certificate metadata |
| `SnapshotBindingDecorator` | Bind exact versions into issuance or claim evidence |

---

## 5. AI Agent Directives

1. Use decorators for cross-cutting document concerns, not giant handlers.
2. Keep each decorator focused and side-effect order explicit.
3. Never let signature verification mutate prior versions in place.
