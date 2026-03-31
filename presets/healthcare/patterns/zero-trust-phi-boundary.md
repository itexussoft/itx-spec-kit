# Zero-Trust PHI Boundary — Attribute-Based Access Control and Data Isolation

> **Domain:** Healthcare
> **Prerequisite patterns:** `hexagonal-architecture.md`, `domain-driven-design.md`

---

## 1. Problem

Protected Health Information (PHI) is subject to HIPAA, GDPR (health
data), and jurisdiction-specific regulations. A perimeter-based security
model is insufficient — breaches happen inside the perimeter. A
**zero-trust** approach assumes every request is untrusted until proven
otherwise, and every data access is authorized at the finest granularity
available.

---

## 2. Core Principles

1. **Never trust, always verify.** Every API call, every service-to-service
   call, every database query must carry and validate an authorization
   context.
2. **Least privilege.** Grant access only to the specific resources
   required for the current operation.
3. **PHI boundary enforcement.** PHI must not leak outside explicitly
   defined trust boundaries — not in logs, not in error messages, not in
   analytics pipelines.

---

## 3. Attribute-Based Access Control (ABAC)

### 3.1 Why ABAC over RBAC?

Role-Based Access Control (RBAC) alone is too coarse for healthcare:

- A "Nurse" role may access patient vitals but not psychiatric notes.
- A "Physician" may access records only for patients in their care panel.
- A "Researcher" may access de-identified data but never identifiable PHI.

ABAC evaluates a **policy** against a set of **attributes** at decision
time:

| Attribute Category | Examples |
|-------------------|---------|
| **Subject** | User role, department, care-team membership, active license status. |
| **Resource** | Resource type (Patient, Observation), sensitivity label (psychiatric, HIV, substance abuse). |
| **Action** | read, write, delete, export. |
| **Environment** | Time of day, IP range, device compliance status, emergency override flag. |

### 3.2 Policy Decision Point (PDP) and Policy Enforcement Point (PEP)

```
  Client Request
       │
       ▼
  ┌────────────────┐       ┌──────────────────┐
  │  PEP            │──────►│  PDP              │
  │  (API Gateway / │       │  (Policy Engine:  │
  │   Service Mesh) │◄──────│   OPA / Cedar /   │
  └────────┬───────┘       │   custom)          │
           │                └──────────────────┘
           │  Allow/Deny + filtered scopes
           ▼
     Service Layer
```

- The **PEP** intercepts every request and queries the **PDP** with the
  full attribute context.
- The **PDP** evaluates policies written in a declarative language
  (Rego for OPA, Cedar for AWS Verified Permissions, XACML).
- The PDP returns `Allow` or `Deny`, optionally with data-filtering
  obligations (e.g., "redact SSN field").

---

## 4. Data Isolation Strategies

### 4.1 Tenant / Patient Isolation

| Strategy | Description | Use When |
|----------|-------------|---------|
| **Row-Level Security (RLS)** | Database policies filter rows by patient or tenant ID injected from the request context. | Multi-tenant SaaS; moderate isolation. |
| **Schema-per-tenant** | Each tenant gets a separate database schema. | Stronger isolation; moderate operational overhead. |
| **Database-per-tenant** | Each tenant gets a separate database instance. | Maximum isolation; high operational overhead. |

For patient-level isolation within a tenant, RLS combined with ABAC
is the recommended approach.

### 4.2 PHI Boundary Enforcement

| Control | Implementation |
|---------|---------------|
| **Structured logging** | PHI fields are stripped or tokenized before writing to log aggregators. Use an allow-list of loggable fields, not a deny-list. |
| **Error responses** | Return generic error messages to clients. PHI details are written only to a secure audit log, never to HTTP response bodies. |
| **Analytics pipeline** | PHI is de-identified (Safe Harbor or Expert Determination method) before entering data warehouses used for analytics. |
| **Encryption at rest** | PHI tables are encrypted with customer-managed keys (CMK). Key rotation policy: at least annually. |
| **Encryption in transit** | mTLS between all services handling PHI. |

---

## 5. Audit Trail

Every PHI access event must be recorded:

```json
{
  "event_id": "uuid",
  "timestamp": "2026-03-26T10:15:30Z",
  "subject": { "user_id": "dr-smith", "role": "physician", "department": "cardiology" },
  "action": "read",
  "resource": { "type": "Patient", "id": "patient-123", "sensitivity": ["standard"] },
  "decision": "allow",
  "policy_version": "v2.3",
  "client_ip": "10.0.1.42"
}
```

- Audit logs are append-only and stored in a tamper-evident system
  (immutable storage, hash chain).
- Retention: per HIPAA, minimum 6 years; per GDPR, as needed for
  legitimate purpose.

---

## 6. Emergency Override ("Break the Glass")

In life-threatening emergencies, a clinician may need access to records
outside their normal authorization scope:

- The system grants access but records the override with elevated audit
  detail (reason, timestamp, overriding user).
- A post-hoc review workflow alerts compliance officers within 24 hours.
- Override frequency is monitored; excessive use triggers investigation.

---

## 7. Integration with Spec-Kit Workflow

| Phase | Zero-Trust PHI Activity |
|-------|------------------------|
| `/speckit.specify` | Identify PHI-bearing resources. Classify data sensitivity levels. Define user/role attribute taxonomy. |
| `/speckit.plan` | Select ABAC engine (OPA, Cedar, custom). Define policies for each resource × action × role. Choose data isolation strategy. Reference this pattern and `fhir-facade.md` in the System Design Plan. |
| `/speckit.tasks` | Separate: ABAC engine setup, PEP middleware, policy definitions, RLS migration, audit logging, emergency-override flow. |
| `/speckit.implement` | Deploy PDP first; wire PEP into every service; write policies; audit-log integration tests; penetration-test PHI boundary. |

---

## References

- NIST SP 800-162, *Guide to Attribute Based Access Control (ABAC)*.
- HIPAA Security Rule, 45 CFR §164.312.
- See also: `fhir-facade.md`, `hexagonal-architecture.md`,
  `domain-driven-design.md`.
