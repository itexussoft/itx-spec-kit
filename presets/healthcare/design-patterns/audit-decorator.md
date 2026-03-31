# Audit Decorator for HIPAA Data-Access Logging

> **Domain:** Healthcare
> **Phase relevance:** Tasks, Implement
> **Extends:** `../../base/design-patterns/decorator-middleware.md`

---

## 1. Context

HIPAA (Health Insurance Portability and Accountability Act) requires that every
access to Protected Health Information (PHI) — reads *and* writes — be logged
in an immutable audit trail. This includes:

- Who accessed the data (identity).
- What data was accessed (resource type and ID).
- When the access occurred (UTC timestamp).
- Why the access was permitted (authorization context / "break-the-glass" flag).
- What operation was performed (read, create, update).

Scattering audit logic across every handler violates DRY and risks gaps. A
Decorator applied at the middleware level guarantees comprehensive, consistent
coverage.

---

## 2. Architecture

```
Request
  → AuthMiddleware (establishes identity)
    → AuditDecorator (logs access BEFORE and AFTER)
      → Handler (performs business logic)
    ← Result + audit confirmation
  ← Response
```

The Audit Decorator wraps **every** handler that touches PHI-bearing
Aggregates. It is registered in the composition root — handlers themselves
are unaware of the audit concern.

---

## 3. Audit Record Structure

| Field | Type | Description |
|-------|------|-------------|
| `audit_id` | `AuditId` | Unique ID for the audit entry. |
| `timestamp` | `UtcTimestamp` | From injected `Clock`, not `DateTime.Now`. |
| `principal` | `PrincipalId` | Authenticated user or service account. |
| `action` | `AuditAction` | `READ`, `CREATE`, `UPDATE`, `DELETE`. |
| `resource_type` | `string` | Aggregate type: `Patient`, `Encounter`, `Observation`. |
| `resource_id` | `ResourceId` | Aggregate root ID. |
| `authorization_context` | `AuthContext` | Role, consent reference, break-the-glass flag. |
| `outcome` | `AuditOutcome` | `SUCCESS`, `FAILURE`, `DENIED`. |
| `detail` | `string?` | Optional — error message on failure. **Must not contain PHI.** |

---

## 4. Implementation Example

```python
class AuditDecorator:
    def __init__(
        self,
        inner: CommandHandler,
        audit_log: AuditLog,
        clock: Clock,
        principal_provider: PrincipalProvider,
    ) -> None:
        self._inner = inner
        self._audit_log = audit_log
        self._clock = clock
        self._principal = principal_provider

    def handle(self, cmd: Command) -> Result:
        principal = self._principal.current()
        resource = extract_resource_metadata(cmd)
        now = self._clock.now_utc()

        result = self._inner.handle(cmd)

        outcome = AuditOutcome.SUCCESS if isinstance(result, Ok) else AuditOutcome.FAILURE
        self._audit_log.append(AuditRecord(
            audit_id=AuditId.generate(),
            timestamp=now,
            principal=principal,
            action=resource.action,
            resource_type=resource.type_name,
            resource_id=resource.id,
            authorization_context=principal.auth_context,
            outcome=outcome,
            detail=None,  # NEVER log PHI here
        ))
        return result
```

---

## 5. Audit Log Requirements

| Requirement | Detail |
|-------------|--------|
| **Immutable.** | Append-only storage; no `UPDATE` or `DELETE` on audit records. |
| **Tamper-evident.** | Hash-chained or written to a WORM (Write Once Read Many) store. |
| **Retained.** | Minimum 6 years per HIPAA; longer if state law requires. |
| **Queryable.** | Support queries by patient ID, principal, date range for compliance investigations. |
| **PHI-free.** | The audit log records *which* resource was accessed (by ID), not the resource content. See `../anti-patterns/logging-phi-data.md`. |

---

## 6. AI Agent Directives

1. **Every** handler that reads or writes a PHI-bearing Aggregate must be
   wrapped by the Audit Decorator — no exceptions.
2. The Audit Decorator is registered in the composition root; handlers
   themselves must **not** contain audit logging code.
3. Audit records must **never** contain PHI data (names, SSNs, diagnoses).
   Only resource IDs and metadata are logged.
4. Use the injected `Clock` for timestamps — never `datetime.now()`.
5. The audit log must be append-only and tamper-evident.
6. "Break-the-glass" access must be audit-logged with an elevated flag and
   trigger a real-time alert.

---

## References

- HIPAA Security Rule §164.312(b) — Audit Controls.
- See also: `../../base/design-patterns/decorator-middleware.md`,
  `../anti-patterns/logging-phi-data.md`.
