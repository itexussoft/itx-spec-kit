# Builder for Immutability

> **Phase relevance:** Tasks, Implement
> **DDD context:** Constructing complex Aggregates and Value Objects that must be immutable after creation.

---

## 1. Intent

A **Builder** separates the construction of a complex object from its
representation, allowing step-by-step assembly while guaranteeing that the
final product is **immutable** and **valid**.

In DDD terms, the Builder acts as a factory for Aggregates or large Value
Objects whose constructors would otherwise require too many parameters.

---

## 2. When to Use

| Signal | Example |
|--------|---------|
| Constructor has more than 4–5 required parameters. | `Trade(id, account, instrument, qty, side, price, timestamp, venue, ...)` |
| Some fields are optional but the object must still be immutable once built. | `NotificationPreferences` with optional channels. |
| Validation spans multiple fields (cross-field invariants). | Start date must precede end date; quantity and price must both be positive. |
| The same construction logic is reused across tests and production code. | Builders double as test fixtures with sensible defaults. |

---

## 3. Structural Rules

| Rule | Rationale |
|------|-----------|
| The Builder is the **only** way to create the target object. | Prevents partially initialized instances. |
| `build()` validates all invariants and returns `Result<T, E>`. | An invalid aggregate never exists. |
| The target object has no public setters. | Immutability is non-negotiable after construction. |
| Builder methods return `self` (fluent API). | Readable, chainable construction. |
| Provide sensible defaults in the Builder for test convenience. | Reduces boilerplate in test fixtures. |

---

## 4. Language-Idiomatic Examples

```python
# Python
from dataclasses import dataclass

@dataclass(frozen=True)
class Trade:
    id: TradeId
    account: AccountId
    instrument: InstrumentId
    quantity: Quantity
    side: OrderSide
    price: Money
    timestamp: UtcTimestamp
    venue: Venue

class TradeBuilder:
    def __init__(self) -> None:
        self._id: TradeId | None = None
        self._account: AccountId | None = None
        # ... fields with None defaults

    def with_id(self, id: TradeId) -> "TradeBuilder":
        self._id = id
        return self

    def with_account(self, account: AccountId) -> "TradeBuilder":
        self._account = account
        return self

    # ... other with_* methods

    def build(self) -> Result[Trade, str]:
        if self._id is None:
            return Err("Trade ID is required")
        if self._account is None:
            return Err("Account is required")
        # ... validate all mandatory fields and cross-field invariants
        return Ok(Trade(
            id=self._id,
            account=self._account,
            instrument=self._instrument,
            quantity=self._quantity,
            side=self._side,
            price=self._price,
            timestamp=self._timestamp,
            venue=self._venue,
        ))
```

```typescript
// TypeScript
class TradeBuilder {
  private id?: TradeId;
  private account?: AccountId;
  // ...

  withId(id: TradeId): this { this.id = id; return this; }
  withAccount(account: AccountId): this { this.account = account; return this; }
  // ...

  build(): Result<Trade, string> {
    if (!this.id) return err("Trade ID is required");
    if (!this.account) return err("Account is required");
    return ok(Object.freeze({
      id: this.id,
      account: this.account,
      // ...
    }));
  }
}
```

```csharp
// C# — leveraging records for immutability
public sealed class TradeBuilder
{
    private TradeId? _id;
    private AccountId? _account;
    // ...

    public TradeBuilder WithId(TradeId id) { _id = id; return this; }
    public TradeBuilder WithAccount(AccountId account) { _account = account; return this; }

    public Result<Trade, string> Build()
    {
        if (_id is null) return "Trade ID is required";
        if (_account is null) return "Account is required";
        return new Trade(_id, _account, /* ... */);
    }
}

public sealed record Trade(
    TradeId Id,
    AccountId Account,
    InstrumentId Instrument,
    Quantity Quantity,
    OrderSide Side,
    Money Price,
    UtcTimestamp Timestamp,
    Venue Venue);
```

---

## 5. Builder as Test Fixture

```python
def a_trade() -> TradeBuilder:
    """Returns a builder pre-filled with valid defaults for testing."""
    return (TradeBuilder()
        .with_id(TradeId.generate())
        .with_account(AccountId("test-account"))
        .with_instrument(InstrumentId("AAPL"))
        .with_quantity(Quantity(100))
        .with_side(OrderSide.BUY)
        .with_price(Money(150_00, Currency.USD))
        .with_timestamp(UtcTimestamp.now())
        .with_venue(Venue("NASDAQ")))
```

Tests call `a_trade().with_price(Money(0, Currency.USD)).build()` to test a
specific edge case without specifying all 8 fields.

---

## 6. AI Agent Directives

1. Use a Builder when constructing Aggregates or Value Objects with more than
   4 parameters.
2. The `build()` method **must** return `Result<T, E>` — never throw on
   invalid input.
3. The resulting object **must** be immutable (frozen dataclass, `readonly`
   record, `Object.freeze`).
4. Provide a `a_<entity>()` test fixture builder with sensible defaults in the
   test suite.
5. **Never** use telescoping constructors or mutable setters on domain objects
   as an alternative.

---

## References

- Gang of Four, *Design Patterns* (1994) — Builder.
- See also: `value-object-and-result-monad.md`.
