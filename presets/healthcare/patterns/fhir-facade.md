# FHIR Facade — Anti-Corruption Layer over Legacy Health Systems

> **Domain:** Healthcare
> **Prerequisite patterns:** `hexagonal-architecture.md`, `domain-driven-design.md`

---

## 1. Problem

Healthcare organizations depend on legacy systems (HL7v2, proprietary
EHRs, custom databases) that expose non-standard, tightly coupled
interfaces. Modern applications need to consume and produce clinical data
using FHIR (Fast Healthcare Interoperability Resources) — the industry
standard for health data exchange. A direct integration couples new
applications to legacy data models and guarantees a maintenance nightmare.

---

## 2. The FHIR Facade Pattern

Place an **Anti-Corruption Layer (ACL)** — the FHIR Facade — between the
modern application layer and every legacy system. The facade:

1. Exposes a **standard FHIR R4 REST API** to internal consumers.
2. Translates FHIR requests into legacy system calls (HL7v2 messages,
   proprietary APIs, direct DB queries).
3. Translates legacy responses back into FHIR Resources.
4. Shields the domain model from legacy data structures entirely.

```
  Modern App (FHIR Client)
          │
          ▼
  ┌─────────────────────────┐
  │      FHIR Facade        │  (Anti-Corruption Layer)
  │                         │
  │  FHIR REST API          │  ← Driving Port (inbound)
  │  Resource Mappers       │  ← Translation logic
  │  Legacy Adapters        │  ← Driven Ports (outbound)
  └──────┬──────────┬───────┘
         │          │
         ▼          ▼
  ┌──────────┐ ┌───────────┐
  │ Legacy   │ │ Legacy    │
  │ EHR      │ │ Lab       │
  │ (HL7v2)  │ │ System    │
  └──────────┘ └───────────┘
```

---

## 3. FHIR Resource Mapping

### 3.1 Mapping Layer

Each legacy system gets a dedicated **Resource Mapper** that implements:

- **Inbound mapping**: FHIR Resource → legacy command/message.
- **Outbound mapping**: legacy response → FHIR Resource.

Mappers are stateless and unit-testable. They live in the adapter layer
(see `hexagonal-architecture.md`).

### 3.2 Common FHIR Resources

| FHIR Resource | Legacy Source (example) | Notes |
|--------------|------------------------|-------|
| `Patient` | MPI (Master Patient Index) | Map legacy patient IDs to FHIR `Identifier`. |
| `Encounter` | ADT messages (HL7v2 A01-A13) | Map admission/discharge events. |
| `Observation` | Lab results (ORU messages) | Map result codes to LOINC via a terminology service. |
| `MedicationRequest` | Pharmacy system | Map drug codes to RxNorm/SNOMED. |
| `Condition` | Problem list in EHR | Map ICD-10 codes; handle code-system versioning. |

### 3.3 Terminology Translation

Legacy systems use local code systems. The facade must integrate a
**Terminology Service** (e.g., HAPI FHIR Terminology Server, Ontoserver)
to translate between local codes and standard terminologies (LOINC,
SNOMED CT, ICD-10, RxNorm).

---

## 4. Caching and Performance

| Concern | Strategy |
|---------|---------|
| Frequently accessed resources (Patient demographics) | Cache with short TTL (5-15 min); invalidate on HL7v2 ADT event. |
| Bulk data export (FHIR $export) | Pre-compute nightly; serve from a read-replica FHIR store. |
| Legacy system latency | Circuit breaker on each legacy adapter; degrade gracefully with cached data. |

---

## 5. Write Path — Command Translation

For write operations (e.g., creating a `MedicationRequest`):

1. The facade validates the inbound FHIR Resource against the FHIR
   profile (StructureDefinition).
2. The Resource Mapper translates to the legacy command format.
3. The legacy adapter submits the command and awaits acknowledgment.
4. On success, the facade returns the FHIR Resource with a server-assigned
   `id` and `meta.versionId`.
5. On failure, return a FHIR `OperationOutcome` with structured error
   details.

---

## 6. Security — PHI Boundary

The FHIR Facade is a **PHI boundary** (see `zero-trust-phi-boundary.md`):

- Enforce OAuth 2.0 / SMART on FHIR authorization on every request.
- Validate scopes (e.g., `patient/Observation.read`) before invoking
  legacy adapters.
- Log all data access events for HIPAA audit requirements.

---

## 7. Integration with Spec-Kit Workflow

| Phase | FHIR Facade Activity |
|-------|----------------------|
| `/speckit.specify` | Identify which FHIR Resources are needed. Catalog legacy systems and their interfaces. |
| `/speckit.plan` | Design Resource Mappers per legacy system. Choose terminology service. Define FHIR profiles (StructureDefinitions). Reference this pattern and `zero-trust-phi-boundary.md` in the System Design Plan. |
| `/speckit.tasks` | Separate: FHIR REST controller, each Resource Mapper, each legacy adapter, terminology integration, caching layer. |
| `/speckit.implement` | Build the facade skeleton with a single resource (Patient) end-to-end; add resources incrementally; validate with FHIR validation tooling (HAPI Validator). |

---

## References

- HL7 FHIR R4 specification: https://hl7.org/fhir/R4/
- Eric Evans, *Domain-Driven Design* — Anti-Corruption Layer.
- See also: `zero-trust-phi-boundary.md`, `hexagonal-architecture.md`,
  `domain-driven-design.md`.
