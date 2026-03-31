# Anti-Pattern: Implicit Time Coupling

> **Domain:** Fintech — Banking
> **Severity:** MUST NOT — causes non-deterministic behavior, test flakiness, and audit inconsistencies.
> **Remedy:** Explicit time injection via a `Clock` abstraction.

---

## 1. Definition

**Implicit time coupling** occurs when domain logic calls a system clock
directly (`DateTime.Now`, `datetime.utcnow()`, `Date.now()`, `Instant.now()`)
instead of receiving the current time as an explicit parameter or injected
dependency.

---

## 2. Why It Is Forbidden in Banking

| Problem | Consequence |
|---------|-------------|
| **Non-deterministic tests.** | Tests that depend on "now" are flaky and cannot assert exact timestamps. |
| **Audit replay impossible.** | Replaying an event-sourced ledger produces different results if "now" shifts. |
| **Time-zone bugs.** | `DateTime.Now` returns local time; financial systems require UTC or explicit business-date semantics. |
| **End-of-day boundary errors.** | A transaction at 23:59:59.999 may land on the wrong business date if clock granularity varies. |
| **Backdating impossible.** | Compensating entries and late-arriving trades need an explicit effective date — not the current wall clock. |

---

## 3. Detection Checklist

The AI agent must flag code when:

- [ ] `datetime.now()`, `datetime.utcnow()` (Python) appears inside domain
  or application logic.
- [ ] `DateTime.Now`, `DateTime.UtcNow`, `DateTimeOffset.Now` (C#) appears
  inside domain logic.
- [ ] `Date.now()`, `new Date()` (JavaScript/TypeScript) appears inside
  domain logic.
- [ ] `Instant.now()`, `LocalDate.now()` (Java/Kotlin) appears inside domain
  logic.
- [ ] Any static clock accessor is called outside of infrastructure adapters
  or composition roots.

---

## 4. Correct Alternative: Clock Injection

### Step 1: Define a Clock Port

```python
from typing import Protocol
from datetime import datetime, timezone

class Clock(Protocol):
    def now_utc(self) -> datetime: ...

class SystemClock:
    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

class FixedClock:
    """For testing."""
    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now_utc(self) -> datetime:
        return self._fixed
```

```typescript
interface Clock {
  nowUtc(): Date;
}

const systemClock: Clock = { nowUtc: () => new Date() };
const fixedClock = (d: Date): Clock => ({ nowUtc: () => d });
```

### Step 2: Inject into Handlers

```python
class CreditAccountHandler:
    def __init__(self, repo: AccountRepository, clock: Clock) -> None:
        self._repo = repo
        self._clock = clock

    def handle(self, cmd: CreditAccount) -> Result[TransactionId, LedgerError]:
        now = self._clock.now_utc()
        account = self._repo.get(cmd.account_id)
        return account.credit(cmd.amount, cmd.effective_date, cmd.reference, recorded_at=now)
```

### Step 3: Distinguish Business Date from Recorded Timestamp

| Concept | Source | Example |
|---------|--------|---------|
| `effective_date` | Provided in the Command (business intent). | The date the transfer should post. |
| `recorded_at` | Injected `Clock.now_utc()` (system timestamp). | When the system processed the command. |

Both are stored on the ledger entry. Neither is derived from a static clock call
inside the domain.

---

## 5. AI Agent Enforcement Rules

1. **NEVER** call `DateTime.Now`, `datetime.utcnow()`, `Date.now()`, or any
   static clock accessor inside domain or application-layer code.
2. **ALWAYS** inject a `Clock` abstraction via the constructor.
3. Use `FixedClock` (or equivalent) in all unit and integration tests to
   guarantee deterministic behavior.
4. Distinguish `effective_date` (business intent, from the Command) from
   `recorded_at` (system timestamp, from the Clock).
5. All timestamps must be UTC. If a business date is needed, derive it
   explicitly from UTC using the account's configured time zone — never from
   the server's local time.

---

## References

- See also: `../design-patterns/command-pattern-ledger.md`,
  `../../base/design-patterns/adapter-anti-corruption.md`.
