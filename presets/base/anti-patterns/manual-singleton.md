# Anti-Pattern: Manual Singleton

> **Severity:** STRICTLY FORBIDDEN — AI agent must never generate this pattern.
> **Remedy:** Dependency Injection / Inversion of Control (IoC) container.

---

## 1. Definition

A **Manual Singleton** is a class that enforces its own single-instance
semantics through a static `instance` field, private constructor, and a global
accessor method (`getInstance()`, `_instance`, `__new__` override, module-level
`_singleton`).

---

## 2. Why It Is Forbidden

| Problem | Consequence |
|---------|-------------|
| **Hidden global state.** | Any class can silently depend on the singleton; dependencies are invisible in the constructor signature. |
| **Untestable.** | Tests cannot substitute a mock or fake without reflection hacks or test-specific reset methods. |
| **Lifecycle opacity.** | The singleton's creation timing is non-deterministic (lazy init, class-load order). |
| **Concurrency hazards.** | Double-checked locking is notoriously error-prone; even when correct it adds complexity for zero benefit. |
| **Violation of SRP.** | The class manages its own lifecycle *and* its business responsibility. |
| **Anti-DDD.** | Singletons bypass the Aggregate/Repository pattern; shared mutable state across bounded contexts destroys isolation. |

---

## 3. Detection Checklist

The AI agent must flag code when:

- [ ] A class has a `private static instance` field (or language equivalent).
- [ ] A `getInstance()` / `shared` / `default` / `current` static method
  returns a cached instance.
- [ ] Python `__new__` is overridden to enforce single instantiation.
- [ ] A module-level variable is used as a de-facto singleton with mutation.

---

## 4. Correct Alternative: Dependency Injection

### Before (Violation)

```python
class NotificationService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def send(self, msg: str) -> None: ...

# Usage — hidden dependency
class OrderHandler:
    def handle(self, cmd):
        NotificationService().send("Order placed")
```

### After (Compliant)

```python
class NotificationService:
    def send(self, msg: str) -> None: ...

class OrderHandler:
    def __init__(self, notifications: NotificationService) -> None:
        self._notifications = notifications

    def handle(self, cmd):
        self._notifications.send("Order placed")

# Composition root — register as singleton lifetime in the IoC container
container.register(NotificationService, lifetime=Singleton)
```

The IoC container manages the singleton lifetime. The class itself has no
knowledge of how many instances exist. Tests inject a fake trivially:

```python
handler = OrderHandler(notifications=FakeNotificationService())
```

---

## 5. When "Single Instance" Is Legitimate

Sometimes you genuinely need exactly one instance (database connection pool,
configuration object). The rule is:

- **Register it as a singleton in the IoC container.** The container enforces
  the lifetime.
- **Inject it through the constructor.** Consumers declare the dependency
  explicitly.
- **Never** let the class enforce its own singularity.

---

## 6. AI Agent Enforcement Rules

1. **NEVER** generate a class with a private constructor + static instance
   accessor in any language.
2. **NEVER** override `__new__` in Python to enforce single instantiation.
3. **ALWAYS** use constructor injection for dependencies. The composition root
   (IoC container, main function) determines lifetimes.
4. If a single-instance lifetime is required, register the class as `Singleton`
   in the container — not in the class itself.
5. Flag any static `getInstance()` or global accessor during code review as
   a mandatory refactoring target.
