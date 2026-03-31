# Decorator & Middleware Pattern

> **Phase relevance:** Tasks, Implement
> **Cross-cutting concerns:** Logging, retries, caching, auth, rate-limiting, distributed tracing.

---

## 1. Intent

A **Decorator** wraps an existing interface implementation to add behavior
*without modifying* the original class. A **Middleware pipeline** chains
multiple decorators in a defined order around a core handler.

This pattern replaces scattered, duplicated cross-cutting logic with composable,
single-responsibility wrappers.

---

## 2. When to Use

| Concern | Decorator/Middleware? |
|---------|----------------------|
| Request logging and timing | Yes |
| Retry with exponential back-off | Yes |
| Circuit breaker | Yes |
| Authorization / RBAC checks | Yes |
| Distributed tracing (span creation) | Yes |
| Input validation (beyond Value Object self-validation) | Yes |
| Caching read-model queries | Yes |
| Business logic inside the Aggregate | **No** — that belongs in the domain |

---

## 3. Structural Rules

| Rule | Rationale |
|------|-----------|
| The decorator implements the **same interface** as the inner component. | Enables transparent stacking — callers don't know about wrappers. |
| One decorator = one concern. | Single Responsibility; easy to add/remove. |
| Order matters: outermost runs first. | Logging before auth before retry before handler. |
| Register decorators in the composition root / IoC container. | Keeps domain code unaware of cross-cutting wrappers. |

---

## 3. Language-Idiomatic Examples

```python
# Python — decorator function wrapping a handler
import functools, time, logging

log = logging.getLogger(__name__)

def with_logging(handler):
    @functools.wraps(handler)
    def wrapper(cmd):
        log.info("Handling %s", type(cmd).__name__)
        start = time.monotonic()
        result = handler(cmd)
        elapsed = time.monotonic() - start
        log.info("Handled %s in %.3fs → %s", type(cmd).__name__, elapsed,
                 "ok" if isinstance(result, Ok) else "err")
        return result
    return wrapper

def with_retry(max_attempts: int = 3, backoff: float = 0.5):
    def decorator(handler):
        @functools.wraps(handler)
        def wrapper(cmd):
            for attempt in range(1, max_attempts + 1):
                result = handler(cmd)
                if isinstance(result, Ok) or attempt == max_attempts:
                    return result
                time.sleep(backoff * (2 ** (attempt - 1)))
            return result
        return wrapper
    return decorator
```

```typescript
// TypeScript — class-based decorator sharing the Handler interface
class LoggingDecorator<C, R> implements CommandHandler<C, R> {
  constructor(private readonly inner: CommandHandler<C, R>) {}

  async handle(cmd: C): Promise<Result<R, DomainError>> {
    console.log(`Handling ${cmd.constructor.name}`);
    const start = performance.now();
    const result = await this.inner.handle(cmd);
    console.log(`Handled in ${(performance.now() - start).toFixed(1)}ms`);
    return result;
  }
}
```

```csharp
// C# — MediatR pipeline behavior (middleware)
public class LoggingBehavior<TReq, TRes> : IPipelineBehavior<TReq, TRes>
    where TReq : IRequest<TRes>
{
    public async Task<TRes> Handle(
        TReq request,
        RequestHandlerDelegate<TRes> next,
        CancellationToken ct)
    {
        _log.LogInformation("Handling {Request}", typeof(TReq).Name);
        var sw = Stopwatch.StartNew();
        var response = await next();
        _log.LogInformation("Handled {Request} in {Elapsed}ms",
            typeof(TReq).Name, sw.ElapsedMilliseconds);
        return response;
    }
}
```

---

## 4. Middleware Pipeline Composition

```
Request
  → LoggingMiddleware
    → AuthMiddleware
      → ValidationMiddleware
        → RetryMiddleware
          → Handler (core logic)
        ← Result
      ← Result
    ← Result
  ← Result
Response
```

Register this pipeline once in the composition root. Individual handlers and
domain code remain completely unaware of the wrappers.

---

## 5. AI Agent Directives

1. **Never** embed logging, retry logic, or auth checks directly inside a
   command handler or domain service. Extract them into a decorator/middleware.
2. Each decorator must implement the **same interface** as the component it
   wraps.
3. Decorators must be registered in the composition root — not instantiated
   inside the domain.
4. When a cross-cutting concern appears in more than one handler, it is a
   **mandatory** candidate for extraction into a middleware.
5. Test decorators independently from the handlers they wrap.

---

## References

- Gang of Four, *Design Patterns* (1994) — Decorator.
- See also: `command-and-handler.md`.
