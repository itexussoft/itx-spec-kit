# Anti-Pattern: Primitive Obsession

> **Severity:** MUST NOT — AI agent must reject code exhibiting this pattern.
> **Remedy:** `../design-patterns/value-object-and-result-monad.md`

---

## 1. Definition

**Primitive Obsession** is the use of raw language primitives (`string`, `int`,
`float`, `bool`, `Guid`) to represent domain concepts that have identity,
validation rules, or semantic meaning beyond the primitive's type.

---

## 2. Why It Is Harmful

| Problem | Consequence |
|---------|-------------|
| **No compile-time safety.** | An `account_id: str` is freely assignable to an `email: str`. |
| **Validation is scattered.** | Every call site must remember to validate the format. |
| **Implicit coupling.** | Changes to the format (e.g., IBAN v2) require shotgun surgery. |
| **Unreadable signatures.** | `def transfer(str, str, int)` tells the reader nothing. |
| **Testing gaps.** | Invalid values slip through because the type system cannot catch them. |

---

## 3. Detection Checklist

The AI agent must flag code when:

- [ ] A function parameter or return type is a bare `str` / `string` / `int`
  that represents a domain concept (ID, email, currency code, amount, date
  range, phone number, postal code, etc.).
- [ ] Two or more primitives always travel together (amount + currency,
  latitude + longitude).
- [ ] A regular expression or format check is applied to the same primitive in
  more than one location.
- [ ] A `Dict[str, Any]` or `Record<string, unknown>` is used to pass around
  a structured domain concept.

---

## 4. Refactoring Steps

1. **Create a Value Object** (see `../design-patterns/value-object-and-result-monad.md`)
   with a validating constructor.
2. **Replace all occurrences** of the raw primitive with the new type.
3. **Move validation logic** into the Value Object constructor — remove
   scattered checks.
4. **Update serialization boundaries** (API controllers, message consumers) to
   parse into the Value Object at the edge.

### Before (Violation)

```python
def create_account(email: str, phone: str, currency: str) -> str:
    if not re.match(r"[^@]+@[^@]+", email):
        raise ValueError("bad email")
    ...
```

### After (Compliant)

```python
def create_account(
    email: EmailAddress,
    phone: PhoneNumber,
    currency: CurrencyCode,
) -> Result[AccountId, DomainError]:
    ...
```

---

## 5. AI Agent Enforcement Rules

1. **NEVER** use `str`, `int`, or `float` as a parameter or field type when the
   value represents a domain concept with validation rules.
2. **ALWAYS** create a Value Object for: IDs, emails, phone numbers, currency
   codes, monetary amounts, dates/ranges, coordinates, percentages, ISINs,
   IBANs, and any other constrained domain value.
3. When reviewing generated code, flag any function signature where two or more
   parameters share the same primitive type — this is a strong signal of
   Primitive Obsession.
4. Serialization/deserialization boundaries (API layer, message consumers) must
   parse raw input into Value Objects **immediately** — primitives must not
   propagate past the application boundary.
