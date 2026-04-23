# Procurement Guarantees Constraints

These constraints define the minimum architectural posture for procurement-guarantee platforms. Treat them as invariants, not as optional guidance.

## Product and Domain Invariants

- Product coverage must be template-driven and support multiple guarantee classes. Local procurement-law variants, buyer wording, and issuer-specific forms are configuration overlays, not core architecture.
- The operative undertaking must remain distinct from the underlying commercial contract and from internal scoring or recommendation outputs.
- Claims, presentations, amendments, expiry, and release are first-class lifecycle concerns. Do not model the domain as "issue once, then archive."

## State and Evidence Invariants

- Preserve separate state and evidence for intake, underwriting, provider execution, amendment, presentation or claim, expiry, and release.
- Runtime history is append-only. Status history, provider-track audit, claim evidence, document versions, network messages, and signing evidence must never be overwritten or physically deleted.
- Issued wording, documentary submissions, and termination evidence must remain reproducible at the exact version used in the business step they support.
- Provider messaging must preserve semantic distinctions between request, operative message, advice, notification, response, and status report.
- Status reporting should preserve status category, status code, and status reasons where available instead of compressing them into one opaque field.

## Integration and Security Invariants

- Provider execution must tolerate multiple transport styles: manual operation, portal interaction, signed APIs, bank-network messages, and structured document exchange.
- Integration boundaries must remain transport-neutral. Do not let one provider protocol redefine the core undertaking model.
- Internal and external APIs should be capability-aligned semantic contracts. Stable contracts require compatibility protection and must not drift with one provider's DTO shape or one channel's endpoint naming.
- High-risk actions must support strong auditability and, where appropriate, step-up authorization, dual control, replay protection, and idempotent processing.
- Evidence envelopes should preserve message-definition identifiers, document types and formats, signature markers, and copy or duplicate provenance when those attributes exist in upstream channels.

## Access and Risk Invariants

- Party-scoped visibility must prevent leakage between applicant, beneficiary, issuer, intermediary, and operator roles.
- Separate action permissions from read visibility. Entitlements should govern what a party may do, while views or redaction profiles govern what a party may see.
- Exposure must be visible at portfolio level: outstanding amount, facility utilization, collateral or cash cover, expiry profile, reductions, and released amount.
- Provider-track and party-scope boundaries must remain explicit in storage, APIs, search, documents, and reporting.
