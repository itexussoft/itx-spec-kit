# Pattern Index (fintech-banking)

## Architectural Patterns
- `event-sourced-ledger.md`: Append-only ledger with event-sourced account state
- `saga-distributed-transactions.md`: Saga orchestration for cross-service transaction flow
- `psd2-api-gateway.md`: PSD2-compliant API gateway for open banking integration

## Code-Level Design Patterns
- `command-pattern-ledger.md`: Command pattern for encapsulating ledger mutations
- `fowler-money-pattern.md`: Safe currency arithmetic using integer minor units

## Anti-Patterns (Forbidden / Demoted)
- `in-place-balance-updates.md`: Forbids direct balance mutation; requires transaction appends
- `implicit-time-coupling.md`: Forbids DateTime.Now in domain logic; requires Clock injection
