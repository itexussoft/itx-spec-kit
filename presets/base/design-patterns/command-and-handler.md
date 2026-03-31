# Command & Handler Pattern

> **Phase relevance:** Tasks, Implement
> **Foundation for:** CQRS, Event-Driven Messaging, Saga Orchestration.

---

## 1. Intent

A **Command** is an immutable data object that represents a request to mutate
the system. A **Handler** is the single function (or class with one public
method) that executes that request.

Separating "what to do" from "how to do it" provides:

- A serializable unit of work suitable for queues, audit logs, and undo.
- A single entry point per mutation, simplifying tracing and authorization.
- Natural alignment with CQRS (Commands mutate; Queries read).

---

## 2. Structural Rules

| Element | Constraint |
|---------|------------|
| **Command** | Immutable DTO. Named as an imperative verb phrase: `PlaceOrder`, `CreditAccount`. Contains only the data required for the mutation — no behavior. |
| **Handler** | One handler per command. Orchestrates validation, Aggregate loading, mutation, and event emission. Returns `Result<T, E>`, not void. |
| **Dispatcher** | Routes a Command to its Handler. Can be a simple dictionary, a mediator library, or the IoC container. |

### 2.1 Separation from Queries

Commands return a Result indicating success/failure and optionally the created
resource ID. They must **never** return rich read models. Use a separate Query
path (read model, projection) for data retrieval.

---

## 3. Language-Idiomatic Examples

```python
# Python
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class PlaceOrder:
    account_id: AccountId
    instrument: InstrumentId
    quantity: Quantity
    side: OrderSide

class PlaceOrderHandler:
    def __init__(self, repo: OrderRepository, events: EventBus) -> None:
        self._repo = repo
        self._events = events

    def handle(self, cmd: PlaceOrder) -> Result[OrderId, DomainError]:
        order = Order.place(cmd.account_id, cmd.instrument, cmd.quantity, cmd.side)
        self._repo.save(order)
        self._events.publish(order.pending_events)
        return Ok(order.id)
```

```typescript
// TypeScript
interface PlaceOrder {
  readonly accountId: AccountId;
  readonly instrument: InstrumentId;
  readonly quantity: Quantity;
  readonly side: OrderSide;
}

class PlaceOrderHandler {
  constructor(
    private readonly repo: OrderRepository,
    private readonly events: EventBus,
  ) {}

  async handle(cmd: PlaceOrder): Promise<Result<OrderId, DomainError>> {
    const order = Order.place(cmd.accountId, cmd.instrument, cmd.quantity, cmd.side);
    await this.repo.save(order);
    await this.events.publish(order.pendingEvents);
    return ok(order.id);
  }
}
```

```csharp
// C#
public sealed record PlaceOrder(
    AccountId AccountId,
    InstrumentId Instrument,
    Quantity Quantity,
    OrderSide Side) : ICommand<OrderId>;

public sealed class PlaceOrderHandler : ICommandHandler<PlaceOrder, OrderId>
{
    public async Task<Result<OrderId, DomainError>> HandleAsync(
        PlaceOrder cmd, CancellationToken ct)
    {
        var order = Order.Place(cmd.AccountId, cmd.Instrument, cmd.Quantity, cmd.Side);
        await _repo.SaveAsync(order, ct);
        await _events.PublishAsync(order.PendingEvents, ct);
        return order.Id;
    }
}
```

---

## 4. Cross-Cutting Concerns via Pipeline

Handlers are wrapped by **middleware** (see `decorator-middleware.md`) to add:

- Logging & distributed tracing
- Authorization checks
- Idempotency enforcement
- Validation (preferably via the Command's Value Objects)
- Transactional boundaries

```
Command → [Logging] → [Auth] → [Validation] → [Transaction] → Handler → Result
```

---

## 5. AI Agent Directives

1. Every write operation exposed by an API or message consumer **must** be
   modelled as an explicit Command + Handler pair.
2. Commands are immutable. Use Value Objects for their fields — never raw
   primitives (see `value-object-and-result-monad.md`).
3. Handlers return `Result<T, E>`. Never throw exceptions for expected
   business outcomes.
4. One handler per command — no "god handler" accepting multiple command types.
5. Use the Dispatcher / Mediator to decouple the API layer from handler
   implementations.

---

## References

- Bertrand Meyer, *Command-Query Separation*.
- Greg Young, *CQRS Documents* (2010).
- See also: `decorator-middleware.md`, `../patterns/event-driven-microservices.md`.
