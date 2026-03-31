# PSD2 API Gateway — BFF and Gateway Patterns for Open Banking

> **Domain:** Fintech Banking
> **Prerequisite patterns:** `hexagonal-architecture.md`, `domain-driven-design.md`

---

## 1. Context

PSD2 (Payment Services Directive 2) mandates that banks expose account
information and payment initiation APIs to licensed Third-Party Providers
(TPPs). These APIs must enforce Strong Customer Authentication (SCA) and
operate under strict consent and security requirements. A dedicated API
Gateway layer — combined with a Backend-for-Frontend (BFF) — isolates
these regulatory concerns from the core banking domain.

---

## 2. Architecture Overview

```
  TPP App / PSU Browser
          │
          ▼
  ┌───────────────────────┐
  │  Open Banking BFF     │  (PSD2 consent UI, SCA orchestration)
  └──────────┬────────────┘
             │
             ▼
  ┌───────────────────────┐
  │  API Gateway          │  (Rate limiting, mTLS termination,
  │                       │   TPP certificate validation,
  │                       │   request routing)
  └──────────┬────────────┘
             │
     ┌───────┴───────┐
     ▼               ▼
  ┌─────────┐  ┌──────────┐
  │ Account │  │ Payment  │    (Core Bounded Contexts)
  │ Info    │  │ Initiate │
  │ Service │  │ Service  │
  └─────────┘  └──────────┘
```

---

## 3. API Gateway Responsibilities

| Concern | Implementation |
|---------|---------------|
| **TPP Identity Verification** | Validate eIDAS QWAC/QSeal certificates on every request. Extract TPP roles (AISP, PISP, CBPII) from the certificate. |
| **Consent Enforcement** | Check the consent token (granted during SCA) against the requested resource scope. Reject requests where consent is expired, revoked, or insufficient. |
| **Rate Limiting** | Per-TPP rate limits aligned with regulatory fair-usage guidelines. |
| **mTLS Termination** | Terminate mutual TLS at the gateway; forward authenticated TPP identity as a trusted header to downstream services. |
| **Request Transformation** | Map Berlin Group / UK Open Banking request formats to internal canonical models. |
| **Audit Logging** | Log every TPP request (method, resource, TPP ID, consent ID, timestamp) to a tamper-evident audit store. |

---

## 4. Backend-for-Frontend (BFF) — SCA Orchestration

The BFF manages the SCA flow for Payment Service Users (PSUs):

### 4.1 SCA Flow

1. **TPP initiates consent request** → Gateway routes to BFF.
2. **BFF redirects PSU to bank's authentication page** (redirect or
   decoupled approach).
3. **PSU authenticates** (password + second factor: OTP, biometric, push).
4. **BFF issues consent token** with scope (accounts, balances, payments)
   and validity period.
5. **TPP uses consent token** for subsequent API calls through the Gateway.

### 4.2 BFF Design Rules

- The BFF is **not** a general-purpose API. It serves only the PSD2
  consent/SCA UI.
- Session state for the SCA flow is short-lived (minutes); store in Redis
  with aggressive TTL.
- The BFF exposes a separate host/port from the API Gateway to enforce
  network-level separation.

---

## 5. Anti-Corruption Layer

The Gateway + BFF act as an **Anti-Corruption Layer** between the external
PSD2 world and the internal banking domain:

- External PSD2 schemas (Berlin Group, UK OB) are translated to internal
  domain commands at the gateway boundary.
- Internal domain events are projected into PSD2-compliant response schemas
  at the gateway boundary.
- The core Account and Payment services never import PSD2-specific types.

---

## 6. Security Checklist

| Control | Requirement |
|---------|------------|
| Certificate pinning | Pin the QTSP root CA; reject self-signed or untrusted certificates. |
| Consent expiry | Maximum consent validity: 90 days (per PSD2 RTS). Re-authentication required beyond this. |
| Token binding | Bind consent tokens to the TPP certificate fingerprint to prevent token theft. |
| Replay protection | Include a unique `x-request-id`; reject duplicates within a sliding window. |
| Data minimization | Return only the data scopes granted in the consent. Never over-share. |

---

## 7. Integration with Spec-Kit Workflow

| Phase | PSD2 Gateway Activity |
|-------|-----------------------|
| `/speckit.specify` | Define which PSD2 APIs are in scope (AIS, PIS, CBPII). Identify TPP roles supported. |
| `/speckit.plan` | Design the SCA flow (redirect vs. decoupled). Choose certificate validation strategy. Map external schemas to internal Bounded Contexts. Reference this pattern in the System Design Plan. |
| `/speckit.tasks` | Separate: gateway mTLS + cert validation, BFF SCA flow, consent store, request transformation per API, audit logging. |
| `/speckit.implement` | Build gateway infrastructure first; add BFF SCA flow; integrate with Account/Payment services; penetration-test the SCA flow. |

---

## References

- European Banking Authority, *PSD2 Regulatory Technical Standards on SCA* (2018).
- Berlin Group, *NextGenPSD2 XS2A Framework*.
- See also: `hexagonal-architecture.md`, `domain-driven-design.md`,
  `event-sourced-ledger.md`.
