# Federated Identity (OIDC/OAuth2) and SSO — SaaS Platform

> **Domain:** SaaS Platform  
> **Prerequisite patterns:** `hexagonal-architecture.md`, `domain-driven-design.md`

---

## 1. Context

Enterprise and B2B SaaS customers expect **Single Sign-On (SSO)** via their corporate IdP (Okta, Azure AD, Google Workspace, etc.). **OpenID Connect (OIDC)** on top of **OAuth2** is the standard for browser and API authentication: the IdP issues **ID tokens** (who the user is) and optionally **access tokens** for APIs.

The application should **validate** tokens and **map** identities to tenants — not reinvent OAuth2 server behavior unless you are explicitly building an IdP product.

---

## 2. High-Level Architecture

```
  User Agent (Browser / Mobile)
           │
           ▼
  ┌────────────────────┐
  │  BFF or SPA        │  Authorization Code + PKCE (public clients)
  └─────────┬──────────┘
            │
            ▼
  ┌────────────────────┐
  │  OIDC IdP          │  SSO, MFA, session at IdP
  │  (tenant-specific  │
  │   or multi-tenant) │
  └─────────┬──────────┘
            │ ID token / access token (JWT)
            ▼
  ┌────────────────────┐
  │  API Gateway       │  JWKS validation, audience/issuer checks
  └─────────┬──────────┘
            │ Trusted claims: sub, org_id, tenant_id, email
            ▼
  ┌────────────────────┐
  │  Domain services   │  Authorization (RBAC/ABAC) inside tenant
  └────────────────────┘
```

---

## 3. Design Rules

| Concern | Guideline |
|---------|-----------|
| **Token validation** | Verify signature (JWKS), `iss`, `aud`, `exp`, and (for access tokens) intended resource. Reject tokens missing required claims. |
| **Tenant binding** | Map IdP `iss` + org claim or configured **enterprise connection** to internal `tenant_id`. Do not trust a client-supplied tenant id without matching IdP metadata. |
| **PKCE** | Use PKCE for SPA and mobile OAuth clients. |
| **Refresh & sessions** | Prefer short-lived access tokens; refresh via secure, HTTP-only cookies or backend-held refresh where applicable. |
| **SCIM** | When customers require automated user lifecycle, expose or integrate SCIM for provision/deprovision synced to IdP groups. |

---

## 4. SSO Across Multiple Products

- Use a **single IdP application** per customer or a federation hub when the customer has multiple IdPs.
- Document **logout** behavior (OIDC RP-initiated logout vs local session only) in the System Design Plan Section 9.

---

## 5. Anti-Corruption at the Edge

- Map OIDC claims to internal **User** and **Membership** value objects in an adapter — core domain stays free of JWT field names.
- Keep **authorization** (what the user may do in this tenant) separate from **authentication** (who they are).

---

## 6. Integration with Spec-Kit Workflow

| Phase | Activity |
|-------|----------|
| `/speckit.specify` | Define login flows (SSO only vs SSO + local), required claims, and tenant provisioning model. |
| `/speckit.plan` | Choose IdP integration (hosted login vs embedded). Document JWKS URL, audiences, mTLS if required. Reference this pattern in Section 9. |
| `/speckit.tasks` | Separate: OAuth callback handlers, token validation middleware, tenant mapping service, SCIM endpoint (if in scope). |
| `/speckit.implement` | Add contract tests for invalid issuer/audience/expired tokens; E2E happy path SSO per tenant. |

---

## References

- OpenID Connect Core 1.0.
- OAuth 2.0 Security Best Current Practice (RFC 8252, PKCE).
- See also: `multi-tenant-data-isolation.md`, `tenant-context-middleware.md`.
