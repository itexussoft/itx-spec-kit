# Multi-Tenant Data Isolation — SaaS Platform

> **Domain:** SaaS Platform  
> **Prerequisite patterns:** `domain-driven-design.md`, `hexagonal-architecture.md`

---

## 1. Problem

Multi-tenant SaaS products must prevent one tenant from reading or mutating another tenant’s data while controlling cost and operational complexity. Isolation failures are security incidents; weak isolation also causes **noisy neighbor** performance issues on shared infrastructure.

---

## 2. Isolation Strategies

| Strategy | Description | Isolation strength | Ops complexity |
|----------|-------------|-------------------|----------------|
| **Shared DB + RLS** | Single schema; `tenant_id` on rows; DB policies enforce filters | Moderate (depends on RLS discipline) | Low |
| **Schema-per-tenant** | One schema per tenant in a shared database instance | Stronger logical separation | Medium |
| **Database-per-tenant** | Dedicated DB (or cluster) per tenant | Maximum isolation | High |
| **Hybrid** | Hot tenants on dedicated resources; long tail on shared + RLS | Variable | Medium |

Choose based on regulatory requirements, tenant size, and contractual isolation SLAs.

---

## 3. Tenant Context Propagation

```
  Client Request
        │
        ▼
  ┌─────────────────┐     Resolve tenant from host / JWT / header
  │  API Gateway    │──────────────────────────────────────────────┐
  └────────┬────────┘                                              │
           │ Trusted tenant_id + optional org claims               │
           ▼                                                       │
  ┌─────────────────┐     Inject into connection/session vars      │
  │  Application    │──────────────────────────────────────────────┤
  └────────┬────────┘                                              │
           │                                                       │
     ┌─────┴─────┬─────────────┬──────────────┐                  │
     ▼           ▼             ▼              ▼                  │
   PostgreSQL   Redis        SQS/Kafka    Object store           │
   (RLS SET)   (key prefix)  (metadata)   (prefix/path) ◄────────┘
```

**Rules:**

- Resolve tenant **once** at the edge; downstream services must not re-derive tenant from untrusted client input alone.
- Pass tenant context via **structured fields** (headers, baggage, message attributes), not implicit globals without request scope.
- Background jobs and cron workers must carry `tenant_id` explicitly; never assume a single-tenant process.

---

## 4. Cache and Queue Isolation

| Layer | Guideline |
|-------|-----------|
| **Cache** | Prefix every key with `tenant:{id}:` (or hash tenant into key namespace). Never share a key across tenants for tenant-scoped entities. |
| **Queues** | Include `tenant_id` in message body or attributes; consumers must filter and enforce before handling. |
| **Search / analytics** | Use separate indexes or strict index filters per tenant where the product exposes cross-tenant risk. |

---

## 5. DDD Mapping

- Model **Tenant** as a boundary concept: aggregates that own tenant-scoped data include `TenantId` as part of their identity or invariants.
- Cross-tenant operations (support tools, billing aggregation) live in **explicit** application services with elevated authorization and audit — not in default user flows.

---

## 6. Integration with Spec-Kit Workflow

| Phase | Activity |
|-------|----------|
| `/speckit.specify` | List tenant-scoped aggregates and data stores. State isolation level and compliance drivers. |
| `/speckit.plan` | Choose RLS vs schema vs DB-per-tenant. Document cache/queue key strategy. Reference `tenant-context-middleware.md`. |
| `/speckit.tasks` | Separate: tenant resolution middleware, RLS migration, repository changes, cache prefixing, message schema updates. |
| `/speckit.implement` | Add integration tests that prove tenant A cannot read tenant B’s rows with a forged client id when context is wrong. |

---

## References

- NIST SP 800-204, *Security Strategies for Microservices-based Application Systems*.
- See also: `federated-identity-oidc.md`, `white-label-theming-architecture.md`, `tenant-context-middleware.md`.
