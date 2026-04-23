---
tags:
  - partner
  - webhook
  - hmac
  - nonce
  - replay
  - idempotency
anti_tags:
  - react
  - ui
  - component
  - toast
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Partner Gateway Security

> **Domain:** Procurement Guarantees

Broker, issuer, beneficiary, and bank-network channels are privileged ingress and egress paths. Protect them as integration boundaries, not as simplified public APIs.

## 1. Architectural Intent

Treat partner and provider connectivity as a first-class integration contour.
This contour is responsible for secure ingress/egress, message normalization,
idempotent delivery semantics, and separation between external transport and
internal undertaking models.

## 2. Integration Shapes to Support

| Shape | Examples |
|-------|----------|
| Signed REST API | Broker submission, issuer callback, beneficiary release portal |
| Webhook | Procurement platform notifications, status updates |
| Bank-network message | MT760 issuance, MT767 amendment, MT765 demand |
| ISO 20022 trade-services message | Issuance, amendment, demand, termination, status report |
| Manual/portal fallback | Human-operated provider workflow with explicit audit |

## 3. Boundary Rules

Recommended architecture:

- one integration context for signed partner APIs and callbacks
- one anti-corruption boundary for bank-network or provider-specific messages
- one normalized internal event model for issuance, amendment, demand, release
- one stable semantic contract per partner-facing boundary, versioned independently from transport adapters

Security controls such as HMAC, nonce, timestamp windows, and idempotency keys
belong to this integration contour, not to unrelated domain services.

## 4. Why it matters

SWIFT, ISO 20022 trade-services, and corporate-bank channels distinguish issuance, amendment, demand, termination, and status reporting. REST and webhook integrations should preserve the same business semantics even if the transport differs.

## Spec-Kit implications

- Plans must describe how replay protection and idempotency are implemented.
- Plans must state whether a changed partner contract is draft, stable, or deliberately version-shifted.
- Integration tests must cover duplicate delivery, stale-signature rejection, and backward compatibility for stable partner contracts.

## References

- SWIFT Category 7 guidance for MT760 issuance, MT767 amendment, and MT765 demand.
- ISO 20022 Trade Services `tsrv` message families for undertakings.
