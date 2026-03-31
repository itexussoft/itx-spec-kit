# Pattern Index (healthcare)

## Architectural Patterns
- `fhir-facade.md`: Facade and ACL layer for safe FHIR interoperability
- `zero-trust-phi-boundary.md`: Zero-trust controls around PHI access boundaries

## Code-Level Design Patterns
- `audit-decorator.md`: Decorator for HIPAA-compliant PHI data-access audit logging
- `fhir-adapter.md`: Anti-Corruption Layer translating domain models to/from FHIR

## Anti-Patterns (Forbidden / Demoted)
- `logging-phi-data.md`: Strictly forbids logging patient identifiers in application logs
