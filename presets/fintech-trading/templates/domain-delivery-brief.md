# Fintech trading — domain delivery brief

## When to use

Fill this in when scoping a feature or plan that affects **orders, market data, risk, or low-latency paths**. It complements the main spec/plan templates from the base preset.

## Context to capture

- **Latency and throughput:** Target SLOs for hot paths; what must stay in-process vs async.
- **Market data:** Feeds, normalization, staleness tolerances, and replay or backfill needs.
- **Order lifecycle:** States, transitions, idempotency, and partial fills or cancels.
- **Risk controls:** Pre-trade checks, position limits, and kill-switch behavior.
- **Availability:** Cell or zone boundaries; degradation modes when a venue or feed is down.
- **Determinism:** Sequencing, clocks, and reproducibility for audits or simulations.

## Out of scope (explicit)

- List what this change deliberately does **not** cover to avoid scope creep.

## Risks and open questions

- Record unresolved market, regulatory, or operational risks to resolve before implementation.
