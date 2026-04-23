---
tags:
  - ledger
  - command
  - idempotency
  - handler
  - transaction
  - account
anti_tags:
  - react
  - ui
  - frontend
  - component
  - button
  - browser
  - palette
  - shortcut
  - keyboard
  - menu
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Command Pattern: Ledger Mutations

> **Domain:** Fintech — Banking
> **Phase relevance:** Tasks, Implement
> **Extends:** `../../base/design-patterns/command-and-handler.md`

---

## 1. Context

In a banking ledger every balance-affecting operation must be:

- **Auditable** — who did what, when, and why.
- **Reversible** — compensating transactions, not `DELETE` statements.
- **Serializable** — suitable for event sourcing and regulatory replay.
- **Idempotent** — retries from message queues must not double-post.

The Command pattern provides a natural unit of work that satisfies all four
requirements.

---

## 2. Ledger Command Structure

Every ledger mutation is a frozen, immutable Command object:

| Field | Type | Purpose |
|-------|------|---------|
| `command_id` | `CommandId` (UUID v7) | Idempotency key. |
| `account_id` | `AccountId` | Target account (Value Object). |
| `amount` | `Money` | Amount with currency (Value Object — see `fowler-money-pattern.md`). |
| `effective_date` | `UtcDate` | Business date of the entry (Value Object). |
| `reference` | `TransactionReference` | External correlation (payment ID, transfer ID). |
| `initiated_by` | `PrincipalId` | Actor who authorized the mutation. |

```python
@dataclass(frozen=True)
class CreditAccount:
    command_id: CommandId
    account_id: AccountId
    amount: Money
    effective_date: UtcDate
    reference: TransactionReference
    initiated_by: PrincipalId
```

---

## 3. Handler Responsibilities

```
CreditAccountHandler
  1. Check idempotency: if command_id already processed → return existing result.
  2. Load Account aggregate from the ledger repository.
  3. Call account.credit(amount, effective_date, reference).
     → Aggregate appends a LedgerEntry (never mutates balance in place).
     → Aggregate emits AccountCredited domain event.
  4. Persist the aggregate (append-only — see anti-patterns/in-place-balance-updates.md).
  5. Publish domain event to the event bus.
  6. Return Result<TransactionId, LedgerError>.
```

---

## 4. Compensating Commands

Reversals are modelled as **new commands**, not modifications:

```python
@dataclass(frozen=True)
class ReverseLedgerEntry:
    command_id: CommandId
    original_transaction_id: TransactionId
    reason: ReversalReason
    initiated_by: PrincipalId
```

The handler loads the original entry, creates a contra entry with the negated
amount, and emits `LedgerEntryReversed`.

---

## 5. Idempotency

- Store the `command_id → result` mapping in a persistent idempotency table.
- Before executing, check the table. If the command was already processed,
  return the stored result without re-executing.
- Use the `command_id` as the deduplication key in message queues (SQS, Kafka).

---

## 6. AI Agent Directives

1. Every ledger mutation **must** be an explicit, immutable Command processed
   by a dedicated Handler.
2. Commands must include an idempotency key (`command_id`) — never rely on
   "at-most-once" delivery from the queue.
3. The Account aggregate must **append** a `LedgerEntry` — never mutate a
   `balance` field directly (see `../anti-patterns/in-place-balance-updates.md`).
4. Reversals are compensating commands — never `UPDATE` or `DELETE` existing
   entries.
5. All monetary fields use the `Money` Value Object (see
   `fowler-money-pattern.md`) — never raw `float` or `int`.
6. The handler must return `Result<T, E>` — never throw for expected business
   failures (insufficient funds, account frozen).

---

## References

- See also: `../../base/design-patterns/command-and-handler.md`,
  `fowler-money-pattern.md`, `../anti-patterns/in-place-balance-updates.md`.
