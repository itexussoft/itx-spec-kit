# Pattern Index (procurement-guarantees)

## Architectural Patterns
- `canonical-undertaking-message-taxonomy.md`: Canonical message families and status semantics for issuance, amendment, demand, termination, and status reporting
- `service-domain-semantics-and-contracts.md`: Capability-aligned service domains, business scenarios, and stable semantic APIs for guarantee platforms
- `configurable-flow-metamodel.md`: Product-template and versioning model for bid bonds, performance guarantees, advance-payment guarantees, and adjacent instruments
- `dual-state-machine-application-track.md`: Separate lifecycle for customer application and issued undertaking with deterministic aggregation and claim handling
- `snapshot-evidence-boundary.md`: Immutable evidence, version history, and presentation packages across issuance, amendment, claim, and release
- `organization-anchor-and-rls-boundary.md`: Party-anchor, data ownership, and scoped visibility for applicant, beneficiary, issuer, surety, and broker actors
- `partner-gateway-security.md`: Secure issuer, broker, beneficiary, and bank-network integration using signed APIs and message adapters
- `exposure-ledger-and-limit-management.md`: Exposure, facility, collateral, and utilization model for outstanding guarantee obligations

## Code-Level Design Patterns
- `transition-guard-command-handler.md`: Command handlers that own legal lifecycle transitions, side effects, and evidence creation
- `step-up-action-guard.md`: High-risk user actions protected by step-up MFA and explicit authorization checks
- `document-evidence-decorator.md`: Decorator pipeline for upload, version, sign, verify, claim-package, and audit actions on documents
- `provider-capability-strategy.md`: Strategy object per issuer or surety capability set instead of hardcoded provider branches
- `presentation-examination-policy.md`: Policy object for compliant examination of claims, demands, amendments, and release requests

## Anti-Patterns (Forbidden / Demoted)
- `hardcoded-flow-by-law-or-bank.md`: Forbids hardcoding country-specific law variants or bank-specific branches into core services
- `implicit-status-bypass.md`: Forbids direct mutation of application and track statuses outside transition guards
- `silent-api-manual-fallback.md`: Forbids hidden mode switches from API to MANUAL when partner delivery fails
- `cross-organization-access-leakage.md`: Forbids cross-organization data and document visibility leaks
- `physical-delete-or-history-overwrite.md`: Forbids destructive delete or overwrite of runtime history, snapshots, and document versions
- `scoring-as-bank-decision.md`: Forbids treating platform scoring as a bank decision or accepted offer
- `provider-coupled-core-domain.md`: Forbids leaking SWIFT fields, insurer payloads, or surety provider DTOs into the core domain model
