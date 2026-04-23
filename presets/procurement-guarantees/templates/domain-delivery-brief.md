# Procurement Guarantees — Domain Delivery Brief

Use this brief when a feature touches procurement guarantees, demand guarantees, surety bonds, standby-adjacent instruments, provider integrations, documentary evidence, claim handling, or exposure management.

Prefer concrete nouns over generic labels. Name the instrument class, the party topology, the lifecycle slice, and the provider boundary. "Guarantee module changes" is not a sufficient description.

## 1. System Slice

- What exact business slice is changing: intake, underwriting, routing, issuance, amendment, presentation or claim, expiry, release, or portfolio monitoring?
- Is this a platform capability, a product-template change, a provider-specific adapter change, or a local market overlay?

## 2. Instrument and Market Model

- Which instrument class is affected: bid bond, performance guarantee, advance-payment guarantee, payment bond, maintenance bond, demand guarantee, surety bond, or standby-adjacent flow?
- Which market convention or operating rule applies: URDG 758, ISP98, buyer-specific wording, bilateral bank wording, local procurement rules, or no formal rulebook?
- Which parts of the undertaking are variable: amount, currency, wording, expiry, reduction schedule, claim conditions, release conditions, or documentary set?

## 3. Party Topology and Ownership

- Who are the applicant or principal, beneficiary or obligee, issuer or guarantor, optional counter-guarantor or advising bank, intermediary, and platform operator?
- Which service domains own each step: application intake, provider track, claim handling, documents and evidence, exposure reporting, access control, notifications, or configuration?
- What is the control record for each affected domain?
- Which party scopes require strict read or write isolation?

## 4. Lifecycle and State

- Which state machines are affected: `Application`, `ApplicationBankTrack`, claim or presentation flow, release or discharge flow, or portfolio projection?
- What are the terminal states and what freezes after they are reached?
- If the feature aggregates provider outcomes, what is the rule for deriving customer-visible application status from multiple tracks?

## 5. Evidence and Documents

- Which documents, signatures, attestations, snapshots, network messages, or release proofs must remain reproducible?
- What is the versioning rule for issued wording, amendments, claim packs, and release evidence?
- Does the feature introduce new documentary checkpoints for issuance, claim examination, or discharge?
- Do exchanged artifacts require canonical preservation of document type, document format, presentation medium, place of presentation, digital signature, or copy or duplicate provenance?

## 6. Provider Boundary

- Is the provider channel manual, portal, signed API, SWIFT or bank network, or file or document exchange?
- What anti-corruption boundary protects the core model from provider-specific payloads, terminology, and status vocabularies?
- Which semantic API or service operation changes, and what is its compatibility posture: draft, stable, or deprecated?
- Which canonical message family changes: request, operative message, advice, notification, response, status report, or evidence envelope?
- What replay protection, idempotency, authentication, signature verification, or dual control assumptions apply?

## 7. Exposure and Commercial Controls

- Which commercial controls matter: facility limit, collateral, cash cover, concentration, outstanding exposure, release amount, or expiry ladder?
- Does the feature change how exposure is created, amended, reduced, claimed, or released?
- Which projections or reports must remain correct after the change?

## 8. Out of Scope

- State what this feature explicitly does not cover, especially local legal customization, bespoke provider wording, unrelated product classes, or a new instrument family that should be modeled as a separate template.

## 9. Risks and Open Questions

- Record unresolved risks around undertaking wording, provider capability mismatches, claim examination semantics, documentary sufficiency, release evidence, exposure accounting, semantic API compatibility, or party isolation before implementation.
