---
tags:
  - service-domain
  - semantic-api
  - business-scenario
  - contracts
  - decomposition
  - procurement
anti_tags:
  - react
  - ui
  - component
  - modal
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Capability-Aligned Service Domains and Semantic APIs

> **Domain:** Procurement Guarantees
> **Prerequisite patterns:** `domain-driven-design.md`, `hexagonal-architecture.md`

Model the procurement-guarantee platform as a set of right-sized service domains aligned to business capabilities, each with stable semantic contracts. Cross-domain flows should be described as business scenarios with explicit preconditions, postconditions, and handoff semantics.

This pattern adapts BIAN's service-domain thinking and semantic API discipline to the guarantee domain without forcing the platform into a bank-specific vocabulary.

## 1. Architectural Intent

Guarantee platforms tend to decay when decomposition follows channels, provider brands,
or local laws instead of durable business capabilities. The result is a patchwork of
`broker-api`, `bank-api`, `rfq-service`, `swift-service`, and `manual-ops-service`
modules that leak concepts into one another and cannot offer stable contracts.

The architectural goal is to define elemental service domains that represent major
functional partitions of the application. Each domain should own a clear business
object boundary and expose a semantic contract that remains stable even if the
transport, provider mix, or jurisdiction changes.

## 2. Recommended Service Domains

| Service Domain | Core Responsibility | Typical Control Record |
|----------------|---------------------|------------------------|
| Product Configuration | Flow definitions, versions, rule publication | `FlowVersion` |
| Party Directory and Access | Party references, party links, entitlements, visibility rules | `OrgReference` |
| Application Intake | Capture and progress the customer or broker request | `Application` |
| Underwriting and Recommendation | Screening, scoring, provider fit, recommendation history | `UnderwritingCase` |
| Undertaking Execution | Provider-track issuance, amendment, expiry, cancellation, release | `ApplicationBankTrack` |
| Claim and Presentation | Demand or claim handling and examination workflow | `PresentationCase` |
| Evidence and Documents | Versioned documents, signatures, snapshots, attestations | `EvidencePackage` |
| Exposure and Facilities | Outstanding liability, utilization, collateral, reductions, releases | `ExposurePosition` |
| Partner Gateway | Semantic partner contracts, authentication, mapping, callbacks | `PartnerExchange` |

Right-sizing matters. A domain should be elemental enough to own one coherent function,
but not so small that every lifecycle step becomes its own pseudo-service.

## 3. Control Records and Sub-Capabilities

Use a long-lived business anchor per service domain. In BIAN terms this resembles a
control record: the stable record around which service operations are organized.

In this preset, examples include:

- `Application` for intake and routing intent
- `ApplicationBankTrack` for provider execution
- `PresentationCase` for a claim or demand journey
- `ExposurePosition` for outstanding undertaking liability

When a domain has meaningful, repeatable sub-capabilities, model them as explicit
subdomains, nested workflows, or structured sub-resources. BIAN calls these behavior
qualifiers. Use the idea only when the decomposition is:

- discrete
- mutually exclusive where appropriate
- collectively complete for the parent capability
- stable across providers and jurisdictions

Do not use behavior-qualifier-style decomposition to disguise arbitrary endpoint sprawl.

## 4. Business Scenarios and Preconditions

Cross-domain work should be described as business scenarios, not as an ad hoc chain of
controller calls. A business scenario names the participating service domains and the
preconditions and postconditions of each handoff.

Example guarantee scenarios:

- application submitted -> underwriting started -> provider track initiated
- amendment requested -> wording regenerated -> provider amendment dispatched
- claim presented -> examination completed -> payment or rejection recorded
- expiry reached -> release evidence captured -> exposure reduced

This keeps lifecycle orchestration explicit and supports transport changes without
rewriting the domain model.

## 5. Semantic API Rules

Expose service-domain APIs in business terms rather than channel-specific DTO language.
The external contract should describe what happened in the guarantee lifecycle, not how
one partner transport happens to encode it.

Recommended rules:

- one semantic API surface per service domain boundary
- operations grouped around the domain's control record
- explicit action semantics for initiate, retrieve, update, evaluate, execute, notify, or cancel style interactions
- provider-facing operations should map cleanly to canonical undertaking message families such as request, advice, notification, response, and status report
- stable versioning policy for externally consumed contracts
- provider-specific payloads mapped at the gateway or adapter edge

An internal implementation can be REST, async messaging, workflow orchestration, or a
hybrid. The semantic contract should survive those choices.

## 6. Stable Contract Posture

Adopt an explicit lifecycle for public or partner-facing contracts. A useful baseline is:

- `DRAFT` for unstable contracts still being shaped
- `STABLE` for contracts that require compatibility protection
- `DEPRECATED` for contracts being retired under a migration plan

This mirrors the practical API-governance posture seen in open banking platforms and
reduces accidental breaking changes to partner integrations.

## Spec-Kit implications

- `/speckit.plan`: name the affected service domains and the control records they own.
- `/speckit.plan`: describe the business scenario and the preconditions or postconditions of each domain handoff.
- `/speckit.tasks`: separate semantic contract changes from provider-adapter changes and internal workflow changes.
- `/speckit.implement`: preserve backward compatibility for stable contracts or document a deliberate version shift.

## References

- BIAN Service Landscape and Semantic API Practitioner Guide.
- ISO20022.PLUS overview of BIAN to ISO 20022+ mappings.
- Open Bank Project API versioning, views, and entitlement-oriented API posture.
