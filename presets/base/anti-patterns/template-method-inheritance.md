# Anti-Pattern: Template Method & Deep Inheritance

> **Severity:** WARNING — AI agent must avoid unless narrowly justified.
> **Remedy:** Strategy pattern, higher-order functions, composition.
> **See:** `../design-patterns/strategy-and-composition.md`

---

## 1. Definition

The **Template Method** pattern defines the skeleton of an algorithm in a base
class, deferring specific steps to subclasses through abstract/virtual methods.
While originally a GoF pattern, it encourages deep inheritance trees that are
rigid, hard to test, and violate composition-over-inheritance principles.

---

## 2. Why It Is Problematic

| Problem | Consequence |
|---------|-------------|
| **Fragile base class.** | Changes to the base class ripple unpredictably into all subclasses. |
| **Inflexible variation.** | Each new behavioral variant requires a new subclass — class explosion. |
| **Hidden control flow.** | The algorithm skeleton lives in the parent; subclass authors must understand the parent's internal sequencing. |
| **Testing difficulty.** | Subclasses inherit test dependencies from the parent; mocking a single step requires subclassing the subclass. |
| **Diamond / multiple inheritance.** | Combining behaviors from two template hierarchies is impossible in single-inheritance languages and fragile in others. |
| **Depth > 2 is a red flag.** | More than two levels of inheritance almost always indicates a design flaw. |

---

## 3. Detection Checklist

The AI agent must flag code when:

- [ ] A base class defines a public method that calls protected/abstract hooks
  (the "template method" pattern).
- [ ] The inheritance tree is deeper than 2 levels.
- [ ] A subclass overrides more than one or two methods of the parent.
- [ ] A developer is creating a new subclass solely to change one step of an
  algorithm.

---

## 4. Refactoring to Strategy / Higher-Order Functions

### Before (Anti-Pattern)

```python
class BaseProcessor:
    def process(self, data):
        validated = self.validate(data)
        transformed = self.transform(validated)
        return self.persist(transformed)

    def validate(self, data): ...      # abstract
    def transform(self, data): ...     # abstract
    def persist(self, data): ...       # abstract

class OrderProcessor(BaseProcessor):
    def validate(self, data): ...
    def transform(self, data): ...
    def persist(self, data): ...

class RefundProcessor(BaseProcessor):
    def validate(self, data): ...
    def transform(self, data): ...
    def persist(self, data): ...
```

### After (Compliant — Strategy Composition)

```python
from typing import Protocol, Callable

class Validator(Protocol):
    def __call__(self, data: RawInput) -> Result[ValidInput, Error]: ...

class Transformer(Protocol):
    def __call__(self, data: ValidInput) -> DomainObject: ...

class Persister(Protocol):
    def __call__(self, obj: DomainObject) -> Result[Id, Error]: ...

class Processor:
    def __init__(self, validate: Validator, transform: Transformer, persist: Persister):
        self._validate = validate
        self._transform = transform
        self._persist = persist

    def process(self, data: RawInput) -> Result[Id, Error]:
        return (self._validate(data)
                .map(self._transform)
                .flat_map(self._persist))

order_processor = Processor(validate_order, transform_order, persist_order)
refund_processor = Processor(validate_refund, transform_refund, persist_refund)
```

No inheritance. Each step is independently testable and replaceable.

---

## 5. When Base Classes Are Acceptable

- **Framework requirements** (e.g., `Controller`, `TestCase`) — but keep them
  thin wrappers; push logic into composed services.
- **Sealed algebraic type hierarchies** representing a closed set of domain
  variants (one level only).

---

## 6. AI Agent Enforcement Rules

1. **Do not** use the Template Method pattern. Prefer Strategy injection or
   higher-order functions.
2. **Do not** create inheritance hierarchies deeper than 2 levels.
3. If a subclass exists solely to override one method, replace the hierarchy
   with a composed object that accepts the varying behavior as a parameter.
4. When reviewing generated code, flag any `abstract` / `virtual` method that
   is called by a public method in the same base class — this is the Template
   Method smell.
