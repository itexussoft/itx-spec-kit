# Anti-Pattern: Classic Visitor Pattern

> **Severity:** FORBIDDEN — AI agent must not generate the classic double-dispatch Visitor.
> **Remedy:** Native pattern matching / switch expressions.

---

## 1. Definition

The classic **Visitor** pattern uses double dispatch (an `accept(Visitor)`
method on every element class plus a `visit(ConcreteElement)` overload per
element in the Visitor interface) to add operations to a type hierarchy without
modifying the types.

---

## 2. Why It Is Forbidden in Modern Code

| Problem | Consequence |
|---------|-------------|
| **Massive boilerplate.** | Every new element requires updating *every* Visitor implementation with a new `visit` overload. |
| **Bidirectional coupling.** | The element must know about the Visitor interface; the Visitor must know about every element type. |
| **Unreadable control flow.** | `accept → visit → double dispatch` is non-obvious to readers. |
| **Modern languages have replaced it.** | Pattern matching in C# (`switch` expressions), TypeScript (discriminated unions + `switch`), Python (`match`), Kotlin (`when`), Rust (`match`), and Java (`sealed` + `switch`) eliminate the need. |

---

## 3. Detection Checklist

The AI agent must flag code when:

- [ ] An interface named `*Visitor` with multiple `visit(ConcreteType)` methods
  is defined.
- [ ] Domain objects have an `accept(Visitor)` method.
- [ ] Double-dispatch is used to route behavior based on runtime type.

---

## 4. Modern Replacement: Pattern Matching

### Before (Anti-Pattern — Classic Visitor)

```java
interface ShapeVisitor {
    void visit(Circle c);
    void visit(Rectangle r);
    void visit(Triangle t);
}

interface Shape {
    void accept(ShapeVisitor visitor);
}

class Circle implements Shape {
    public void accept(ShapeVisitor v) { v.visit(this); }
}

class AreaCalculator implements ShapeVisitor {
    public void visit(Circle c) { /* ... */ }
    public void visit(Rectangle r) { /* ... */ }
    public void visit(Triangle t) { /* ... */ }
}
```

### After (Compliant — Pattern Matching)

```python
# Python 3.10+
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Circle:
    radius: float

@dataclass(frozen=True)
class Rectangle:
    width: float
    height: float

type Shape = Circle | Rectangle

def area(shape: Shape) -> float:
    match shape:
        case Circle(radius=r):
            return math.pi * r ** 2
        case Rectangle(width=w, height=h):
            return w * h
```

```typescript
// TypeScript — discriminated union
type Shape =
  | { kind: "circle"; radius: number }
  | { kind: "rectangle"; width: number; height: number };

function area(shape: Shape): number {
  switch (shape.kind) {
    case "circle": return Math.PI * shape.radius ** 2;
    case "rectangle": return shape.width * shape.height;
  }
}
```

```csharp
// C# — switch expression on sealed hierarchy
public abstract record Shape;
public sealed record Circle(double Radius) : Shape;
public sealed record Rectangle(double Width, double Height) : Shape;

public static double Area(Shape shape) => shape switch
{
    Circle c => Math.PI * c.Radius * c.Radius,
    Rectangle r => r.Width * r.Height,
    _ => throw new InvalidOperationException(),
};
```

---

## 5. Exhaustiveness Guarantee

Modern pattern matching provides compile-time exhaustiveness checks (C#, Rust,
Kotlin sealed classes). If the language doesn't (Python, TypeScript), add a
runtime guard:

```python
match shape:
    case Circle(): ...
    case Rectangle(): ...
    case _:
        raise AssertionError(f"Unhandled shape type: {type(shape)}")
```

---

## 6. AI Agent Enforcement Rules

1. **NEVER** generate the classic Visitor pattern (double-dispatch
   accept/visit).
2. **ALWAYS** use native pattern matching (`match`, `switch` expression, `when`)
   for operations that vary by type.
3. For closed type hierarchies, use sealed/union types to enable exhaustiveness
   checking.
4. If the language version does not support pattern matching (Java < 17,
   Python < 3.10), use a dictionary dispatch keyed on a type discriminator —
   not a Visitor.
