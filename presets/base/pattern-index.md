# Pattern Index (base)

## Architectural Patterns
- `foundational-principles.md`: KISS, YAGNI, DRY, SOLID, and Separation of Concerns as AI-first design principles
- `domain-driven-design.md`: Bounded Contexts, Aggregates, Entities, and Value Objects
- `hexagonal-architecture.md`: Ports-and-adapters architecture to isolate domain logic
- `clean-architecture.md`: Dependency rule and use-case oriented architecture
- `modular-monolith.md`: Strong module boundaries inside a monolithic deployment
- `event-driven-microservices.md`: Asynchronous event-based integration across services
- `transactional-outbox.md`: Reliable event publishing using transactional outbox
- `e2e-testing-strategy.md`: E2E testing rules: one test per journey, containers over mocks, naming conventions
- `cli-orchestrator-architecture.md`: AI-first architecture for CLI tools, workflow engines, and automation scripts
- `asynchronous-event-loop-architecture.md`: Single-process asyncio daemons for concurrent I/O integration (log watch, chat, HTTP sidecars)

## Code-Level Design Patterns
- `value-object-and-result-monad.md`: DDD Value Objects and Result Monad error handling over exceptions
- `strategy-and-composition.md`: Strategy pattern to eliminate conditional chains; composition over inheritance
- `command-and-handler.md`: Command pattern as the tactical foundation for mutations, CQRS, and messaging
- `adapter-anti-corruption.md`: Adapters and ACLs to isolate the domain from external systems
- `decorator-middleware.md`: Decorators and middleware pipelines for cross-cutting concerns
- `state-machine-pattern.md`: Explicit state machines for complex entity lifecycles
- `builder-for-immutability.md`: Builders to construct complex immutable DDD Aggregates

## Anti-Patterns (Forbidden / Demoted)
- `primitive-obsession.md`: Forbids raw strings/ints for domain concepts
- `anemic-domain-model.md`: Forbids pure data classes with externalized logic
- `manual-singleton.md`: Strictly forbids manual Singleton; enforces DI/IoC
- `template-method-inheritance.md`: Warns against deep inheritance; enforces Strategy/HOF
- `visitor-boilerplate.md`: Forbids classic Visitor; enforces native pattern matching
- `over-engineered-cli.md`: Forbids applying DDD/Hexagonal enterprise patterns to tool-class projects
