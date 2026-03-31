# Anti-Pattern: In-Place Balance Updates

> **Domain:** Fintech — Banking
> **Severity:** STRICTLY FORBIDDEN — triggers audit failures and reconciliation errors.
> **Remedy:** Append-only ledger entries; derived balances.

---

## 1. Definition

An **in-place balance update** directly mutates a stored balance field:

```sql
UPDATE accounts SET balance = balance + 100.00 WHERE id = 'acct-123';
```

or in application code:

```python
account.balance += amount
```

---

## 2. Why It Is Forbidden

| Problem | Consequence |
|---------|-------------|
| **No audit trail.** | The previous balance is overwritten; regulators cannot trace how the balance was derived. |
| **Lost-update race condition.** | Two concurrent transactions read the same balance, both add, one write is lost. |
| **Reconciliation impossible.** | Without individual entries, you cannot reconcile the ledger against counterparty records. |
| **Compensation is destructive.** | Reversing a `+= 100` requires a `-= 100` — but if another transaction occurred in between, the result is wrong. |
| **Regulatory non-compliance.** | Banking regulations (SOX, PSD2, Basel III) require immutable, auditable transaction records. |

---

## 3. Detection Checklist

The AI agent must flag code when:

- [ ] A `balance` field is directly incremented or decremented (`+=`, `-=`,
  `SET balance = balance + ...`).
- [ ] An `UPDATE` statement modifies a monetary balance column.
- [ ] A method named `setBalance`, `updateBalance`, or `adjustBalance` exists
  on an Account entity.
- [ ] The Account aggregate has a mutable `balance` field.

---

## 4. Correct Alternative: Append-Only Ledger

### Architecture

```
LedgerEntry (immutable, append-only)
  ├── entry_id: EntryId
  ├── account_id: AccountId
  ├── amount: Money            ← positive for credits, negative for debits
  ├── effective_date: UtcDate
  ├── reference: TransactionReference
  ├── command_id: CommandId    ← idempotency key
  └── created_at: UtcTimestamp

Balance = SUM(LedgerEntry.amount) WHERE account_id = X
```

### Implementation

```python
@dataclass
class Account:
    _id: AccountId
    _entries: tuple[LedgerEntry, ...]
    _pending_entries: list[LedgerEntry]

    @property
    def balance(self) -> Money:
        return sum((e.amount for e in self._entries), Money.zero(self._currency))

    def credit(self, amount: Money, date: UtcDate, ref: TransactionReference) -> Result[LedgerEntry, LedgerError]:
        entry = LedgerEntry.credit(self._id, amount, date, ref)
        self._pending_entries.append(entry)
        self._emit(AccountCredited(self._id, amount, entry.entry_id))
        return Ok(entry)
```

### Materialized Balance (Performance)

For read-heavy paths, maintain a **materialized balance view** that is
recalculated from the ledger entries:

```sql
CREATE MATERIALIZED VIEW account_balances AS
  SELECT account_id, currency, SUM(amount_minor) AS balance_minor
  FROM ledger_entries
  GROUP BY account_id, currency;
```

The view is refreshed asynchronously or via event-driven projection — never by
mutating a balance column.

---

## 5. AI Agent Enforcement Rules

1. **NEVER** generate code that directly mutates a `balance` field on an
   account or any financial entity.
2. **ALWAYS** model balance changes as immutable, append-only `LedgerEntry`
   records.
3. The `balance` property must be a **derived computation** (sum of entries),
   not a stored mutable field.
4. Use a materialized view or event-sourced projection for read performance —
   never a mutable column.
5. Every entry must reference the originating `CommandId` for idempotency and
   audit.
6. Reversals create a new contra entry — never delete or modify an existing
   entry.

---

## References

- See also: `../design-patterns/command-pattern-ledger.md`,
  `../design-patterns/fowler-money-pattern.md`,
  `../../base/patterns/event-sourced-ledger.md` (if present).
