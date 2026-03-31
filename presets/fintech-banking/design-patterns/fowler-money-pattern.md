# Fowler Money Pattern

> **Domain:** Fintech — Banking
> **Phase relevance:** Tasks, Implement
> **Extends:** `../../base/design-patterns/value-object-and-result-monad.md`

---

## 1. Context

Financial arithmetic on raw `float` or `double` is fundamentally broken:

```python
>>> 0.1 + 0.2
0.30000000000000004
```

In banking, a single rounding error on a high-volume ledger compounds into
regulatory-reportable discrepancies. The **Money pattern** (Martin Fowler,
*Patterns of Enterprise Application Architecture*) provides a safe abstraction.

---

## 2. Core Rules

| Rule | Detail |
|------|--------|
| **Integer minor units.** | Store amounts as integers in the smallest currency unit (cents, pence, pips). `$12.34` → `1234` cents. |
| **Currency is mandatory.** | `Money` is always a pair: `(amount_minor: int, currency: CurrencyCode)`. Adding `USD` to `EUR` is a compile/runtime error. |
| **Immutable.** | Arithmetic returns a new `Money` instance; the original is unchanged. |
| **Banker's rounding.** | When division produces a remainder, use half-even (banker's) rounding. Alternatively, use Fowler's allocation algorithm. |
| **Allocation over division.** | Splitting $10 three ways: `[334, 333, 333]` cents (total preserved) — never `333.33 * 3 = 999.99`. |

---

## 3. Language-Idiomatic Implementation

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class Currency(Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"

@dataclass(frozen=True, slots=True)
class Money:
    amount_minor: int
    currency: Currency

    def __post_init__(self) -> None:
        if not isinstance(self.amount_minor, int):
            raise TypeError("amount_minor must be int (minor units)")

    def __add__(self, other: Money) -> Money:
        self._assert_same_currency(other)
        return Money(self.amount_minor + other.amount_minor, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._assert_same_currency(other)
        return Money(self.amount_minor - other.amount_minor, self.currency)

    def allocate(self, ratios: list[int]) -> list[Money]:
        """Fowler allocation: distributes amount across ratios with zero remainder loss."""
        total_ratio = sum(ratios)
        base = [Money((self.amount_minor * r) // total_ratio, self.currency) for r in ratios]
        remainder = self.amount_minor - sum(m.amount_minor for m in base)
        for i in range(remainder):
            base[i] = Money(base[i].amount_minor + 1, self.currency)
        return base

    def _assert_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(self.currency, other.currency)
```

```typescript
class Money {
  constructor(
    readonly amountMinor: number,  // integer
    readonly currency: Currency,
  ) {
    if (!Number.isInteger(amountMinor))
      throw new DomainError("amountMinor must be integer");
  }

  add(other: Money): Money {
    this.assertSameCurrency(other);
    return new Money(this.amountMinor + other.amountMinor, this.currency);
  }

  allocate(ratios: number[]): Money[] {
    const total = ratios.reduce((a, b) => a + b, 0);
    const results = ratios.map(r => new Money(Math.floor(this.amountMinor * r / total), this.currency));
    let remainder = this.amountMinor - results.reduce((a, m) => a + m.amountMinor, 0);
    for (let i = 0; remainder > 0; i++, remainder--)
      results[i] = new Money(results[i].amountMinor + 1, this.currency);
    return results;
  }

  private assertSameCurrency(other: Money): void {
    if (this.currency !== other.currency)
      throw new CurrencyMismatchError(this.currency, other.currency);
  }
}
```

---

## 4. Serialization & Storage

| Layer | Representation |
|-------|---------------|
| Domain | `Money(amount_minor: int, currency: Currency)` |
| Database | `amount_minor BIGINT NOT NULL`, `currency CHAR(3) NOT NULL` — two columns, never one. |
| API (JSON) | `{ "amount": "12.34", "currency": "USD" }` — string to avoid float truncation. Parse to `Money` at the API boundary. |
| Ledger | Stored as-is on the `LedgerEntry`. The balance is computed by summing entries — never stored as a mutable field. |

---

## 5. AI Agent Directives

1. **NEVER** use `float`, `double`, or `Decimal` (unless the language has a
   true fixed-point decimal type with explicit scale) for monetary amounts.
2. **ALWAYS** represent money as an integer in minor units paired with a
   currency code.
3. **NEVER** add or compare `Money` instances with different currencies without
   an explicit exchange-rate conversion step.
4. Use Fowler's **allocation algorithm** when splitting amounts — never
   division followed by rounding.
5. At the API boundary, accept monetary amounts as **strings** in JSON and
   parse immediately into the `Money` Value Object.
6. Database columns must store `amount_minor` and `currency` as separate
   columns — never a combined string like `"12.34 USD"`.

---

## References

- Martin Fowler, *Patterns of Enterprise Application Architecture* (2002) — Money pattern.
- See also: `../../base/design-patterns/value-object-and-result-monad.md`,
  `../anti-patterns/in-place-balance-updates.md`.
