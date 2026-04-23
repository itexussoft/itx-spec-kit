# Procurement Guarantees Overlay

This overlay treats procurement guarantees as a configurable platform for issued undertakings, provider execution, documentary evidence, and portfolio exposure. It should guide plans toward stable domain boundaries instead of one-off workflows tailored to a single issuer, buyer, broker, or jurisdiction.

## Domain Posture

1. Model procurement guarantees as a reusable undertaking platform, not as a single local process or one customer-specific implementation.
2. Preserve the distinction between the `Application` lifecycle and the provider-track lifecycle. Intake, underwriting, and routing are not the same consistency boundary as issuance, amendment, claim, expiry, or release.
3. Treat the market as multi-party by default: applicant or principal, beneficiary or obligee, issuer or guarantor, optional counter-guarantor or advising bank, intermediary, and platform operator.
4. Support multiple instrument classes through templates and versioned policy, including bid bonds, performance guarantees, advance-payment guarantees, payment bonds, and maintenance or warranty instruments.
5. Preserve append-only evidence for issuance, amendment, presentation, examination, claim, expiry, cancellation, and release.
6. Treat scoring, recommendation, and underwriting outputs as decision support. The operative undertaking exists only after issuance or confirmation by the responsible provider.
7. Keep jurisdiction-specific rules, buyer forms, issuer wording, and local procurement variants in templates, policies, or adapters. They must not become unconditional branches in the core domain.
8. Prefer capability-aligned service domains with stable semantic contracts over channel-led decomposition. Partner APIs, provider adapters, and internal modules should align to durable business capabilities such as application intake, undertaking execution, claim handling, evidence, and exposure.

## Planning Obligations

9. During `/speckit.plan`, evaluate `service-domain-semantics-and-contracts.md`, `canonical-undertaking-message-taxonomy.md`, `configurable-flow-metamodel.md`, `dual-state-machine-application-track.md`, `snapshot-evidence-boundary.md`, `organization-anchor-and-rls-boundary.md`, `partner-gateway-security.md`, and `exposure-ledger-and-limit-management.md` from `.specify/patterns/` for applicability.
10. If a feature changes lifecycle behavior, name the affected phase explicitly: intake, underwriting, routing, issuance, amendment, presentation or claim, expiry, or release.
11. If a feature changes provider execution, state whether the boundary is manual operation, portal interaction, signed API, bank-network messaging, or document exchange, and define the anti-corruption strategy.
12. If a feature changes evidence or claim behavior, explain how documentary reproducibility, examination rules, and release or termination evidence remain auditable.
13. If a feature changes exposure, collateral, undertaking amount, or release semantics, explain how utilization, outstanding liability, reduction rules, and portfolio reporting remain correct.
14. If a feature changes an internal or external API, name the affected service domain, the owned control record, and the compatibility posture of the contract.
15. If a feature changes provider messaging, name the canonical message family involved: request, operative message, advice, notification, response, status report, or evidence envelope.

## AI Agent Rules

16. Do not collapse provider-track state into a single application status field for convenience.
17. Do not treat local legal terminology as the domain model itself. Use neutral core concepts and map local wording at template or adapter boundaries.
18. Do not propose designs that overwrite history, mutate issued documents in place, or erase claim and release evidence.
19. Do not let provider payloads, portal-specific endpoint names, or local procurement vocabulary redefine the platform's semantic API.
20. Do not flatten requests, advice, notifications, responses, and status reports into one generic "status update" concept.
