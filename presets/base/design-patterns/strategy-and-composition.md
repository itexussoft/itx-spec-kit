# Strategy Pattern & Composition Over Inheritance

> **Phase relevance:** Tasks, Implement
> **Supersedes:** Massive if/else or switch blocks; deep inheritance hierarchies.

---

## 1. Problem

Business rules frequently branch on type, status, or configuration:

```python
# BAD — combinatorial if/else
if order.type == "market":
    ...
elif order.type == "limit":
    ...
elif order.type == "stop_loss":
    ...
```

Adding a new branch requires editing the existing function — violating
Open/Closed and creating merge conflicts.

---

## 2. Strategy Pattern (Modern Form)

A Strategy is a pluggable algorithm selected at runtime. In modern code it is
typically a **function**, **lambda**, or **protocol/interface with a single
method** — not a class hierarchy.

### 2.1 Implementation Rules

| Rule | Rationale |
|------|-----------|
| Define the strategy as a callable protocol or functional interface. | Keeps it lightweight; avoids class explosion. |
| Register strategies in a dictionary or IoC container — never in a conditional chain. | Adding a variant is additive, not mutative. |
| Inject the strategy through the constructor or method parameter. | Testable in isolation; no hidden globals. |
| Prefer higher-order functions when the strategy is a single operation. | A lambda or function reference replaces an entire class. |

### 2.2 Language-Idiomatic Examples

```python
# Python — callable protocol + registry
from typing import Protocol, Dict

class PricingStrategy(Protocol):
    def calculate(self, order: Order) -> Money: ...

PRICING: Dict[str, PricingStrategy] = {
    "market": MarketPricing(),
    "limit": LimitPricing(),
    "stop_loss": StopLossPricing(),
}

def price_order(order: Order) -> Money:
    strategy = PRICING[order.type]
    return strategy.calculate(order)
```

```typescript
// TypeScript — Record of functions
type PricingStrategy = (order: Order) => Money;

const pricing: Record<OrderType, PricingStrategy> = {
  market: (o) => o.quantity.times(o.marketPrice),
  limit: (o) => o.quantity.times(o.limitPrice),
  stop_loss: (o) => computeStopLoss(o),
};

const priceOrder = (order: Order): Money => pricing[order.type](order);
```

```csharp
// C# — delegate or Func<Order, Money>
var pricing = new Dictionary<OrderType, Func<Order, Money>>
{
    [OrderType.Market] = o => o.Quantity * o.MarketPrice,
    [OrderType.Limit] = o => o.Quantity * o.LimitPrice,
    [OrderType.StopLoss] = ComputeStopLoss,
};
```

---

## 3. Composition Over Inheritance

Inheritance should be shallow (one level, at most two) and reserved for true
"is-a" relationships. For *behavioral variation*, compose objects from smaller
collaborators instead of extending a base class.

### 3.1 When Inheritance Is Acceptable

- Sealed/final type hierarchies modelling a closed domain discriminator
  (e.g., `Shape = Circle | Rectangle`).
- Framework-mandated base classes (e.g., `Controller` in ASP.NET) — but keep
  them thin and push logic into composed services.

### 3.2 When Inheritance Is Forbidden

| Smell | Refactor To |
|-------|-------------|
| More than 2 levels of inheritance. | Compose with Strategy or Decorator. |
| Overriding methods just to change one step of an algorithm. | Use Strategy injection. |
| "Template Method" pattern with abstract hooks. | Higher-order function accepting the varying step. |
| Protected mutable state shared across hierarchy. | Explicit collaborator passed via constructor. |

---

## 4. AI Agent Directives

1. **Never** write an if/else or switch chain that dispatches on a type
   discriminator with more than two branches. Refactor to a Strategy registry.
2. **Never** introduce a class hierarchy deeper than two levels for behavioral
   variation. Use composition and delegation.
3. When adding a new business variant, the change must be *additive*
   (new strategy registration) — not *mutative* (editing an existing conditional).
4. Prefer language-native functional primitives (lambdas, function references)
   as strategies unless the strategy carries its own state.

---

## References

- Gang of Four, *Design Patterns* (1994) — Strategy.
- See also: `../anti-patterns/template-method-inheritance.md`.
