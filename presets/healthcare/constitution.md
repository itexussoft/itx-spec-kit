# Healthcare Overlay

## Domain Rules

1. Treat PHI and patient-linked identifiers as sensitive by default.
2. Apply consent and access-control checks to all patient data access flows.
3. Maintain traceable audit events for patient-data read/write operations.
4. Align exchange payload design with FHIR interoperability where applicable.

## Architectural Design Requirements

5. During `/speckit.plan`, evaluate `fhir-facade.md` and `zero-trust-phi-boundary.md` from `.specify/patterns/` for applicability. If the feature accesses patient data, zero-trust PHI boundary must be justified or explicitly rejected with rationale.
6. The System Design Plan must address PHI boundary controls in Section 9 (Non-Functional Requirements) and HIPAA compliance for any feature that reads or writes patient-linked data.
