# Value Object & Result Monad

> **Phase relevance:** Tasks, Implement
> **Supersedes:** Raw primitive types for domain concepts; unstructured exception throwing for control flow.

---

## 1. Value Object (DDD Tactical)

A Value Object is an immutable, side-effect-free object defined entirely by its
attributes. It carries domain meaning that a raw `string` or `int` never can.

### 1.1 When to Introduce a Value Object

| Signal | Example |
|--------|---------|
| A primitive appears in more than one Aggregate with validation rules. | `email`, `currency_code`, `order_id` |
| Two primitives always travel together. | `(amount, currency)` → `Money` |
| The primitive has format constraints. | IBAN, ISO 8601 duration, UUID |
| Business logic performs math or comparison on the value. | Date ranges, percentages |

### 1.2 Construction Rules

- **Validate on creation.** The constructor (or factory method) must reject
  invalid state. A Value Object that exists is, by definition, valid.
- **Immutable.** No setters, no mutation methods. Derive new instances instead.
- **Structural equality.** Two Value Objects with identical attributes are equal.
- **Self-documenting.** The type name replaces inline comments:
  `EmailAddress` is clearer than `# validated email string`.

### 1.3 Language-Idiomatic Examples

```python
# Python — using frozen dataclass
from dataclasses import dataclass
import re

@dataclass(frozen=True, slots=True)
class EmailAddress:
    value: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", self.value):
            raise ValueError(f"Invalid email: {self.value}")
```

```typescript
// TypeScript — branded type + factory
type EmailAddress = string & { readonly __brand: unique symbol };

function EmailAddress(raw: string): EmailAddress {
  if (!/^[^@]+@[^@]+\.[^@]+$/.test(raw))
    throw new DomainError(`Invalid email: ${raw}`);
  return raw as EmailAddress;
}
```

```csharp
// C# — record struct (zero-alloc)
public readonly record struct EmailAddress
{
    public string Value { get; }
    public EmailAddress(string value)
    {
        if (!Regex.IsMatch(value, @"^[^@]+@[^@]+\.[^@]+$"))
            throw new DomainException($"Invalid email: {value}");
        Value = value;
    }
}
```

---

## 2. Result Monad (Error Handling)

Exceptions are for *exceptional* circumstances (I/O failures, null dereferences).
**Domain validation failures and expected business errors must flow through a
Result type**, making the error path explicit in the type signature.

### 2.1 Core Contract

A Result is a discriminated union: `Success<T>` | `Failure<E>`.

| Principle | Detail |
|-----------|--------|
| No exception for expected errors | `InsufficientFunds` is a known business outcome, not an exception. |
| Composable | Results chain via `map` / `flatMap` / `bind` without nested try/catch. |
| Explicit | The caller *sees* the error channel in the return type. |
| Exhaustive | Pattern matching forces handling of both branches. |

### 2.2 Language-Idiomatic Examples

```python
# Python — lightweight Result (or use the `result` library)
from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, TypeVar, Union

T = TypeVar("T")
E = TypeVar("E")

@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T

@dataclass(frozen=True)
class Err(Generic[E]):
    error: E

Result = Union[Ok[T], Err[E]]

def withdraw(account: Account, amount: Money) -> Result[Transaction, str]:
    if account.balance < amount:
        return Err("Insufficient funds")
    # ... perform withdrawal
    return Ok(transaction)
```

```typescript
// TypeScript — discriminated union
type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };

function withdraw(account: Account, amount: Money): Result<Transaction, string> {
  if (account.balance.lessThan(amount))
    return { ok: false, error: "Insufficient funds" };
  // ... perform withdrawal
  return { ok: true, value: transaction };
}
```

```csharp
// C# — OneOf or custom Result<T, E>
public readonly record struct Result<T, E>
{
    // ... Success/Failure factory methods, Match(), Map(), Bind()
}
```

### 2.3 Anti-Pattern: Exception-Driven Control Flow

```python
# BAD — exception as control flow
try:
    account.withdraw(amount)
except InsufficientFundsError:
    return "Not enough money"
```

This hides the error path from the type system, encourages pokémon catching
(`except Exception`), and breaks composability.

---

## 3. Combining the Two

Value Objects and Result Monads reinforce each other:

```
raw input → Value Object factory (returns Result)
         → on Ok: pass Value Object into Aggregate method
         → on Err: surface domain error to caller without throwing
```

**The AI agent MUST:**

1. Replace every raw `string`, `int`, or `float` that carries domain meaning
   with a Value Object.
2. Return `Result<T, E>` (or language equivalent) from any operation that can
   fail for *business* reasons.
3. Reserve exceptions exclusively for infrastructure faults and programming
   errors (null refs, I/O timeouts).
4. Never catch a broad `Exception` / `Error` base class inside domain logic.

---

## References

- Eric Evans, *Domain-Driven Design* (2003) — Value Objects.
- Scott Wlaschin, *Domain Modeling Made Functional* (2018) — Result type.
- See also: `../anti-patterns/primitive-obsession.md`.
