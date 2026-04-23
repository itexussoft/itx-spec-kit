# Procurement Guarantees Glossary

Use neutral, portable terminology in architecture and code. Local legal wording, buyer forms, and issuer-specific labels should map onto these concepts rather than replace them.

## Parties and Roles

- **Applicant / Principal**: Party requesting the instrument and whose performance, payment, or obligation is being supported.
- **Beneficiary / Obligee**: Party in whose favor the undertaking is issued and who may present a demand or claim.
- **Issuer / Guarantor / Surety Provider**: Bank, insurer, bonding company, or surety provider responsible for issuing the undertaking.
- **Counter-guarantor / Advising Bank**: Institution supporting local issuance, advising the undertaking, or backing another issuer in a multi-bank topology.
- **Broker / Advisor / Intermediary**: Party assisting placement, routing, or document collection without becoming the legal issuer.
- **Platform Operator**: Party operating the software platform, configuration layer, and cross-party workflow controls.

## Instruments and Market Terms

- **Undertaking**: The operative guarantee, bond, or similar instrument issued by the responsible provider.
- **Demand guarantee**: Independent undertaking payable against a complying demand under agreed terms or market rules such as URDG 758.
- **Surety bond**: Three-party undertaking where the surety responds to principal default in favor of the obligee.
- **Standby letter of credit**: Adjacent instrument often sharing transport or evidence channels, but governed by a distinct ruleset.
- **Bid bond / Bid security**: Instrument protecting the buyer if a bidder withdraws, refuses to sign, or fails to furnish post-award security.
- **Performance guarantee / Performance bond**: Instrument protecting the beneficiary against non-performance or defective performance.
- **Advance-payment guarantee**: Instrument securing return of an advance if contractual conditions are not satisfied.
- **Payment bond**: Instrument protecting subcontractors, suppliers, or counterparties from non-payment.
- **Warranty / Maintenance bond**: Instrument covering defects or remediation obligations during the warranty or maintenance period.

## Runtime Model

- **Service Domain**: Capability-aligned application boundary that owns a coherent business responsibility and exposes a semantic contract.
- **Business Scenario**: Cross-domain choreography that names participating service domains together with the preconditions and postconditions of each handoff.
- **Semantic API**: Stable set of business-facing operations exposed by a service domain, independent from provider-specific transport payloads.
- **Service Operation**: One business operation exposed by a semantic API, such as initiating underwriting, issuing an undertaking, or recording a presentation.
- **Control Record**: Long-lived business anchor around which a service domain organizes its operations. In this preset, examples include `Application`, `ApplicationBankTrack`, and `PresentationCase`.
- **Behavior Qualifier**: BIAN term for a stable sub-capability within a service domain. Use it only as a decomposition hint for durable subflows, not as a substitute for aggregate design.
- **FlowDefinition**: Configurable product template that defines the shape of a guarantee class.
- **FlowVersion**: Immutable published version of a product template used by a concrete runtime journey.
- **ScoringRuleSetVersion**: Versioned underwriting, screening, or recommendation ruleset attached to a flow definition.
- **Application**: Intake and underwriting workflow before or around issuance.
- **ApplicationBankTrack**: Provider-specific execution track for an application. In broader market language, this is the issuer track or provider track.
- **INITIAL snapshot**: First provider-facing capture of business fields, documents, and commercial terms at submission or handoff.
- **UPDATE snapshot**: Additive snapshot for clarification, amendment, supplementary documents, or changed commercial terms.

## Claims, Evidence, and Termination

- **Presentation / Demand**: Claim package submitted by the beneficiary under the undertaking.
- **Examination**: Provider-side assessment of whether a presentation complies with undertaking terms and documentary requirements.
- **Issuance advice**: Communication that conveys or advises an issued undertaking to another party without redefining the undertaking model.
- **Issuance notification**: Event-style message announcing that issuance occurred or was recorded.
- **Amendment**: Change to commercial terms, wording, amount, expiry, or documentary conditions after initial issuance.
- **Amendment request**: Request to alter an issued undertaking before the change becomes operative.
- **Amendment response**: Accept, reject, or otherwise record a party position on a proposed amendment.
- **Non-extension**: Notice or request stating that an auto-extending undertaking should not roll forward to the next period.
- **Termination notice**: Message or evidence that the undertaking expired, was cancelled, or otherwise terminated.
- **Extend-or-pay**: Demand pattern requiring the issuer either to extend the undertaking or to honor payment.
- **Demand refusal**: Provider-side refusal or rejection of a demand, usually with recorded reasons.
- **Demand withdrawal**: Withdrawal of a previously submitted demand or claim package.
- **Status report**: Message that communicates undertaking status together with category, code, and optional reasons.
- **Release / Discharge**: Formal end of the undertaking through expiry, cancellation, return, discharge confirmation, or other termination evidence.
- **Documentary evidence**: Versioned documents, signatures, attestations, message payloads, and audit artifacts required to reproduce a legal or operational step.

## Risk, Security, and Transport

- **Exposure**: Outstanding provider liability or platform-tracked obligation associated with active undertakings.
- **Facility / Line**: Commercial limit against which issuance and outstanding exposure are measured.
- **Collateral / Cash Cover**: Assets, deposits, or pledged resources securing provider exposure.
- **OrgReference**: Shared party anchor used to derive visibility, ownership, and policy scope across actors.
- **RLS**: Row-level security used to isolate party-scoped and provider-scoped data.
- **View**: Read-side visibility profile that determines which fields, documents, or projections a role may see, including redacted or blurred variants where required.
- **Entitlement**: Explicit permission to perform an action through an API or workflow. Entitlements govern what a party may do; views govern what a party may see.
- **MessageDefinitionIdentifier**: Canonical identifier of the external message type or schema used for traceability and mapping of provider exchanges.
- **Status category**: Broad lifecycle bucket for a status report, separate from the detailed status code and reasons.
- **Status reason**: Structured explanation attached to a status or refusal.
- **Document type**: Semantic classification of a document included in issuance, amendment, demand, or termination flows.
- **Document format**: Encoding or file representation of a document exchanged with a partner.
- **Presentation medium**: Medium through which presentation or demand may be submitted, such as paper, electronic, or mixed channels.
- **Place of presentation**: Contractually defined place or endpoint where demands and supporting documents must be presented.
- **Copy / Duplicate marker**: Provenance flag indicating whether a message or document is an original, copy, or duplicate transmission.
- **Step-up MFA**: Additional authentication proof required for high-risk actions such as approval, issuance acceptance, claim handling, or release authorization.
- **MT760 / MT767 / MT765**: SWIFT message families commonly used for issuance, amendment, and demand flows in guarantee operations.
