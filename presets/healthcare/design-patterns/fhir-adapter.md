# FHIR Adapter: Domain-to-FHIR Translation

> **Domain:** Healthcare
> **Phase relevance:** Tasks, Implement
> **Extends:** `../../base/design-patterns/adapter-anti-corruption.md`

---

## 1. Context

HL7 FHIR (Fast Healthcare Interoperability Resources) is the standard for
healthcare data exchange. The domain model used internally is optimized for
business logic, while FHIR resources are optimized for interoperability.

These two models **must not** be conflated. The FHIR Adapter is an
Anti-Corruption Layer that translates between the internal domain model and
the external FHIR representation.

---

## 2. Architecture

```
[Domain Core]
    │
    ├── Patient (domain Aggregate)
    ├── Encounter (domain Aggregate)
    └── Observation (domain Aggregate)
    │
    ↓ Port: FhirGateway (interface in domain layer)
    │
[FHIR Adapter — infrastructure layer]
    │
    ├── PatientFhirTranslator    (Domain Patient ↔ FHIR Patient)
    ├── EncounterFhirTranslator  (Domain Encounter ↔ FHIR Encounter)
    └── ObservationFhirTranslator
    │
    ↓ HTTP / FHIR REST API
    │
[External FHIR Server / EHR System]
```

---

## 3. Translation Rules

| Direction | Responsibility |
|-----------|---------------|
| **Domain → FHIR (outbound)** | Translate domain Aggregates into FHIR JSON resources for external publication or API responses. |
| **FHIR → Domain (inbound)** | Parse incoming FHIR resources at the API boundary and map to domain Value Objects / Commands. Reject invalid FHIR before it enters the domain. |

### 3.1 Field Mapping Principles

- **Explicit mapping only.** No automatic serialization. Every field is
  intentionally mapped.
- **FHIR extensions for custom fields.** Domain concepts without a FHIR
  standard field go into FHIR extensions with a project-specific URL.
- **CodeableConcept → Value Object.** FHIR `CodeableConcept` fields map to
  typed domain enums or Value Objects, not raw strings.
- **Reference resolution.** FHIR references (`Reference(Patient/123)`) resolve
  to domain `PatientId` Value Objects at the adapter boundary.

### 3.2 Example: Patient Translator

```python
class PatientFhirTranslator:
    def to_fhir(self, patient: Patient) -> dict:
        return {
            "resourceType": "Patient",
            "id": str(patient.id),
            "identifier": [
                {"system": "urn:oid:2.16.840.1.113883.4.1", "value": str(patient.mrn)}
            ],
            "name": [{"family": patient.name.family, "given": [patient.name.given]}],
            "birthDate": patient.date_of_birth.isoformat(),
            "gender": patient.gender.to_fhir_code(),
        }

    def from_fhir(self, resource: dict) -> Result[CreatePatientCommand, FhirValidationError]:
        try:
            mrn = MedicalRecordNumber(resource["identifier"][0]["value"])
            name = PatientName(
                family=resource["name"][0]["family"],
                given=resource["name"][0]["given"][0],
            )
            dob = DateOfBirth.parse(resource["birthDate"])
            gender = Gender.from_fhir_code(resource.get("gender", "unknown"))
            return Ok(CreatePatientCommand(mrn=mrn, name=name, date_of_birth=dob, gender=gender))
        except (KeyError, IndexError, ValueError) as e:
            return Err(FhirValidationError(str(e)))
```

---

## 4. FHIR Validation

- Validate incoming FHIR resources against the FHIR R4 (or R5) schema
  **before** translation.
- Use a FHIR validator library (e.g., `fhir.resources` for Python,
  `@types/fhir` for TypeScript) for structural validation.
- Domain-specific validation happens *after* translation, inside the domain
  layer (Value Object constructors, Aggregate guards).

---

## 5. Versioning & Profiles

- Pin the FHIR version (`R4`, `R5`) in the adapter module. Do not mix
  versions.
- If the system publishes FHIR resources, define a FHIR **StructureDefinition**
  (profile) for each resource type to document required fields and extensions.
- Store profiles in `docs/fhir-profiles/` for reference.

---

## 6. AI Agent Directives

1. **NEVER** let FHIR resource types (`Bundle`, `Patient`, `Observation`)
   appear in domain layer code. They belong exclusively in the adapter.
2. **ALWAYS** translate FHIR resources into domain Commands or Value Objects at
   the adapter boundary — before entering the domain.
3. Translation functions must be **pure and stateless** — no side effects, no
   I/O.
4. Validate FHIR structure at the adapter boundary; validate business rules in
   the domain layer.
5. FHIR extensions for custom fields must use a project-specific URL namespace.
6. The adapter is covered by contract tests comparing expected FHIR output
   against golden fixtures.

---

## References

- HL7 FHIR R4 Specification: https://hl7.org/fhir/R4/
- See also: `../../base/design-patterns/adapter-anti-corruption.md`,
  `../patterns/fhir-facade.md` (architectural pattern).
