# Fintech banking — domain delivery brief

## When to use

Fill this in when scoping a feature or plan that touches **accounts, payments, ledger, or open banking**. It complements the main spec/plan templates from the base preset.

## Context to capture

- **Regulatory / compliance:** Which regimes apply (e.g. PSD2, local banking rules)? What must be evidenced (audit, consent, strong customer authentication)?
- **Money movement:** Currencies, settlement windows, idempotency keys, and reconciliation expectations.
- **Ledger model:** Event-sourced vs other; how balances and postings are derived; invariants (no silent balance mutation).
- **Open banking / APIs:** Third-party access, consent scopes, rate limits, and gateway responsibilities.
- **Cross-service consistency:** Sagas or outbox; failure compensation; duplicate submission handling.
- **Operational:** Cutover, feature flags, and backward compatibility for existing account holders.

## Out of scope (explicit)

- List what this change deliberately does **not** cover to avoid scope creep.

## Risks and open questions

- Record unresolved regulatory, fraud, or data-quality risks to resolve before implementation.
