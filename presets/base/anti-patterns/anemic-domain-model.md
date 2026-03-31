# Anti-Pattern: Anemic Domain Model

> **Severity:** MUST NOT — AI agent must reject code exhibiting this pattern.
> **Remedy:** Place business logic inside Aggregates and Domain Services.

---

## 1. Definition

An **Anemic Domain Model** consists of domain classes that contain only data
(fields, getters, setters) with all business logic externalized into "service"
classes. The domain objects are effectively DTOs masquerading as a domain layer.

---

## 2. Why It Is Harmful

| Problem | Consequence |
|---------|-------------|
| **Invariant violations.** | Any service can mutate the object into an invalid state because the object has no guards. |
| **Feature envy.** | Services reach into entity internals — a classic code smell. |
| **Duplicate logic.** | Multiple services implement the same business rule because the "owner" (the entity) doesn't enforce it. |
| **Untestable domain.** | Testing requires instantiating services + mocks instead of simply calling `entity.do_something()`. |
| **False DDD.** | The team believes it is doing DDD because classes are named "Entity" and "Repository," but the domain is hollow. |

---

## 3. Detection Checklist

The AI agent must flag code when:

- [ ] A domain class has only public fields/properties and no methods that
  enforce business rules.
- [ ] An "Application Service" or "Domain Service" directly reads and writes
  fields of an entity instead of calling a method *on* the entity.
- [ ] Entity state is validated *outside* the entity (e.g., in a controller
  or service layer).
- [ ] A class named `*Service` performs logic that references a single entity's
  fields — this logic belongs on the entity.

---

## 4. Refactoring Steps

### Before (Violation)

```python
@dataclass
class Order:
    id: str
    status: str
    items: list
    total: float

class OrderService:
    def cancel(self, order: Order) -> None:
        if order.status != "open":
            raise ValueError("Cannot cancel")
        order.status = "cancelled"
        order.total = 0.0
```

### After (Compliant)

```python
@dataclass
class Order:
    _id: OrderId
    _status: OrderState
    _items: tuple[OrderItem, ...]
    _total: Money

    def cancel(self) -> Result[None, DomainError]:
        if self._status != OrderState.OPEN:
            return Err(DomainError("Cannot cancel a non-open order"))
        self._status = OrderState.CANCELLED
        self._emit(OrderCancelled(self._id))
        return Ok(None)
```

The business rule ("only open orders can be cancelled") now lives inside the
entity. The service merely orchestrates infrastructure:

```python
class CancelOrderHandler:
    def handle(self, cmd: CancelOrder) -> Result[None, DomainError]:
        order = self._repo.get(cmd.order_id)
        result = order.cancel()
        if isinstance(result, Ok):
            self._repo.save(order)
        return result
```

---

## 5. AI Agent Enforcement Rules

1. **NEVER** generate a domain entity or aggregate that is a pure data
   container (all public fields, no behavior methods).
2. **ALWAYS** place business invariants (state guards, calculations,
   validations) inside the Aggregate or Entity that owns the data.
3. Application Handlers/Services orchestrate *infrastructure* (load, save,
   publish). They **call** domain methods — they do not *contain* domain logic.
4. If a method on a service accesses more than one field of a single entity
   to make a business decision, that method **must** be moved onto the entity.
5. Domain events are emitted *from within* the Aggregate, not from the service.

---

## References

- Martin Fowler, "AnemicDomainModel" (2003).
- Eric Evans, *Domain-Driven Design* (2003).
