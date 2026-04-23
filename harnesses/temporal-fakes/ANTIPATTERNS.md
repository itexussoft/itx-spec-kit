# Temporal Fakes Anti-Patterns

1. Drift without contract tests: fake and real APIs diverge silently.
2. Consumer-owned fake logic for provider behavior: ownership should stay close to provider contracts.
3. Simulator creep: emulating internals instead of the externally observable contract.
4. Mocks disguised as fakes: no state, no time axis, no fidelity claim.
5. Wall-clock non-determinism: tests rely on sleep instead of injected/controlled clock.
6. Unbounded scenario registry: uncontrolled growth without review or cleanup.
7. Fault injection without steady-state assertions: no meaningful signal from chaos runs.
8. Transport-coupled domain model: state machine trapped in HTTP handlers and hard to reuse.
