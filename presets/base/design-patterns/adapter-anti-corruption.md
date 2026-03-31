# Adapter & Anti-Corruption Layer

> **Phase relevance:** Tasks, Implement
> **DDD context:** Anti-Corruption Layer (ACL) from the Context Map.

---

## 1. Intent

An **Adapter** translates between the domain model and an external system's
interface. An **Anti-Corruption Layer** is a strategic DDD pattern that uses
Adapters (and optionally Facades) to prevent a foreign model from leaking into
the domain.

Together they guarantee that:

- Domain code depends only on domain-defined interfaces (ports).
- Third-party SDK types, REST DTOs, and legacy schemas never appear in
  Aggregate methods or domain events.
- Replacing or upgrading an external dependency changes only the adapter
  implementation — not the domain.

---

## 2. Structural Rules

| Layer | Responsibility |
|-------|---------------|
| **Port (domain)** | An interface expressing what the domain *needs* in domain language: `PaymentGateway`, `IdentityVerifier`. |
| **Adapter (infrastructure)** | Implements the port by calling the actual external API. Translates external DTOs to/from domain Value Objects. |
| **Facade (optional)** | Simplifies a complex external API surface into a smaller, focused interface before the Adapter translates it. |
| **Translator** | A pure mapping function converting between the external schema and the domain model. Stateless and unit-testable. |

### 2.1 Hexagonal Alignment

```
[Domain Core] ←port— [Adapter] ←http/sdk— [External System]
```

The port is defined inside the domain layer. The adapter is wired in the
composition root (IoC container). Domain code never imports adapter packages.

---

## 3. Language-Idiomatic Examples

```python
# Port — domain layer
class PaymentGateway(Protocol):
    def charge(self, customer: CustomerId, amount: Money) -> Result[PaymentId, PaymentError]: ...

# Adapter — infrastructure layer
class StripePaymentAdapter:
    def __init__(self, client: stripe.Client) -> None:
        self._client = client

    def charge(self, customer: CustomerId, amount: Money) -> Result[PaymentId, PaymentError]:
        try:
            intent = self._client.payment_intents.create(
                amount=amount.to_minor_units(),
                currency=amount.currency.value,
                customer=str(customer),
            )
            return Ok(PaymentId(intent.id))
        except stripe.CardError as e:
            return Err(PaymentError.card_declined(str(e)))
```

```typescript
// Port
interface PaymentGateway {
  charge(customer: CustomerId, amount: Money): Promise<Result<PaymentId, PaymentError>>;
}

// Adapter
class StripePaymentAdapter implements PaymentGateway {
  constructor(private readonly client: Stripe) {}

  async charge(customer: CustomerId, amount: Money): Promise<Result<PaymentId, PaymentError>> {
    try {
      const intent = await this.client.paymentIntents.create({
        amount: amount.toMinorUnits(),
        currency: amount.currency,
        customer: customer.value,
      });
      return ok(PaymentId(intent.id));
    } catch (e) {
      if (e instanceof Stripe.errors.StripeCardError)
        return err(PaymentError.cardDeclined(e.message));
      throw e; // infrastructure fault — let it propagate
    }
  }
}
```

---

## 4. Anti-Corruption Layer for Legacy Systems

When integrating with a legacy monolith or partner API whose model conflicts
with the domain:

1. **Never map legacy types 1:1 into domain objects.** Define your own domain
   model and translate explicitly.
2. **Isolate the translation in a dedicated module** (`acl/` or
   `adapters/legacy/`). No domain file imports from this module.
3. **Version the translator.** Legacy APIs change without warning; the ACL
   absorbs the impact.
4. **Test the translator** with recorded contract fixtures (see consumer-driven
   contract tests).

---

## 5. AI Agent Directives

1. **Every** external dependency (payment provider, email service, SMS gateway,
   partner API, legacy database) must be accessed through a port+adapter pair.
2. Domain code must **never** import third-party SDK types. If `stripe.Customer`
   appears in domain logic, it is a violation.
3. Adapter constructors receive the external client via DI — no global
   instantiation.
4. Translation functions between external and domain types must be pure,
   stateless, and covered by unit tests.
5. When integrating with a system whose model differs significantly from the
   domain, wrap the adapter in a full Anti-Corruption Layer module.

---

## References

- Eric Evans, *Domain-Driven Design* (2003) — Anti-Corruption Layer.
- Alistair Cockburn, *Hexagonal Architecture* (2005) — Ports & Adapters.
- See also: `../patterns/hexagonal-architecture.md`.
