# Anti-Pattern: Logging PHI Data

> **Domain:** Healthcare
> **Severity:** STRICTLY FORBIDDEN — HIPAA violation; potential civil and criminal penalties.
> **Remedy:** Log only resource IDs, operation metadata, and correlation tokens.

---

## 1. Definition

**Logging PHI (Protected Health Information)** means writing patient-
identifiable data — names, dates of birth, Social Security numbers, medical
record numbers, diagnoses, lab results, addresses, or any of the 18 HIPAA
identifiers — into application logs, error messages, debug output, or
exception stack traces.

---

## 2. Why It Is Strictly Forbidden

| Problem | Consequence |
|---------|-------------|
| **HIPAA violation.** | Fines of $100–$50,000 per violation, up to $1.5M/year per category. Criminal penalties for willful neglect. |
| **Log exfiltration.** | Logs are often shipped to third-party aggregators (Datadog, Splunk, ELK) — PHI in logs means PHI on third-party infrastructure. |
| **Uncontrolled retention.** | Logs are retained per ops policy (30–90 days), not per HIPAA's minimum necessary / retention rules. |
| **Search exposure.** | Full-text search on log aggregators makes PHI trivially discoverable by anyone with log access. |
| **Incident scope expansion.** | A log storage breach becomes a PHI breach, requiring OCR notification and patient notification. |

---

## 3. The 18 HIPAA Identifiers (Never Log)

1. Names
2. Geographic data (address, ZIP)
3. Dates (birth, admission, discharge, death) — except year
4. Phone numbers
5. Fax numbers
6. Email addresses
7. Social Security numbers
8. Medical record numbers
9. Health plan beneficiary numbers
10. Account numbers
11. Certificate/license numbers
12. Vehicle identifiers / serial numbers
13. Device identifiers / serial numbers
14. Web URLs
15. IP addresses
16. Biometric identifiers
17. Full-face photographs
18. Any other unique identifying number, characteristic, or code

---

## 4. Detection Checklist

The AI agent must flag code when:

- [ ] A `log.*()` or `console.*()` call includes a variable that could contain
  PHI (patient name, MRN, SSN, DOB, diagnosis code).
- [ ] An exception message includes PHI fields:
  `raise ValueError(f"Invalid patient: {patient.name}")`.
- [ ] A structured log field contains a PHI attribute:
  `logger.info("processed", extra={"patient_name": patient.name})`.
- [ ] An error response body includes PHI in the detail message.
- [ ] Debug/trace logging dumps entire domain objects that contain PHI.

---

## 5. Compliant Logging Pattern

### What to Log

| Safe to Log | Example |
|-------------|---------|
| Resource ID (opaque) | `patient_id=pat-a1b2c3` |
| Operation type | `action=CREATE_ENCOUNTER` |
| Correlation / trace ID | `trace_id=abc-123` |
| Outcome | `outcome=SUCCESS` |
| Timestamp (UTC) | `timestamp=2025-07-15T14:30:00Z` |
| Error *category* | `error=VALIDATION_FAILED` |

### What to NEVER Log

| Forbidden | Example of Violation |
|-----------|---------------------|
| Patient name | `log.info(f"Processing {patient.name}")` |
| Date of birth | `log.debug(f"DOB: {patient.dob}")` |
| Diagnosis | `log.error(f"Diagnosis {dx.code}: {dx.description}")` |
| SSN / MRN | `log.info(f"MRN: {patient.mrn}")` |
| Lab results | `log.debug(f"Result: {observation.value}")` |

### Implementation

```python
logger.info(
    "encounter_created",
    patient_id=str(encounter.patient_id),
    encounter_id=str(encounter.id),
    action="CREATE_ENCOUNTER",
    outcome="SUCCESS",
    trace_id=context.trace_id,
)
```

```typescript
logger.info({
  msg: "encounter_created",
  patientId: encounter.patientId.value,
  encounterId: encounter.id.value,
  action: "CREATE_ENCOUNTER",
  outcome: "SUCCESS",
  traceId: context.traceId,
});
```

---

## 6. Exception Handling

Exceptions must **never** embed PHI in the message:

```python
# BAD
raise DomainError(f"Patient {patient.name} (MRN: {patient.mrn}) not eligible")

# GOOD
raise DomainError(f"Patient {patient.id} not eligible for requested service")
```

Internal error details for debugging are written to the **audit log** (which
has HIPAA-compliant access controls and retention), not to application logs.

---

## 7. AI Agent Enforcement Rules

1. **NEVER** include any of the 18 HIPAA identifiers in log statements, error
   messages, or exception messages.
2. **ALWAYS** log only opaque resource IDs (`patient_id`, `encounter_id`),
   operation metadata, and correlation tokens.
3. When generating `log.*()` or `console.*()` calls, scan every interpolated
   variable — if it could contain PHI, replace it with the resource ID.
4. Exception messages must reference entities by **ID only** — never by name,
   MRN, SSN, or any PHI field.
5. Structured log schemas must be reviewed against the 18-identifier list
   before shipping.
6. For debugging PHI-related issues, use the HIPAA-compliant audit log — not
   application logs.

---

## References

- HIPAA Privacy Rule §164.514 — De-identification.
- HIPAA Security Rule §164.312(b) — Audit Controls.
- See also: `../design-patterns/audit-decorator.md`.
