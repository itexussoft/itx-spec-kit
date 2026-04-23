---
tags:
  - strategy
  - provider
  - issuer
  - surety
  - capability
anti_tags:
  - react
  - ui
  - component
  - dropdown
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Strategy: Provider Capability Selection

> **Domain:** Procurement Guarantees
> **Phase relevance:** Tasks, Implement

---

## 1. Intent

Use the **Strategy** pattern to encapsulate provider-specific capabilities such
as issuance channel, amendment support, claim API support, release rules, and
message formats.

---

## 2. Structure

```python
class ProviderCapabilityStrategy(Protocol):
    def issue(self, cmd: IssueUndertaking) -> IssueResult: ...
    def amend(self, cmd: AmendUndertaking) -> AmendResult: ...
    def register_claim(self, cmd: RegisterClaim) -> ClaimResult: ...
```

Concrete strategies:

- `PortalProviderStrategy`
- `RestApiProviderStrategy`
- `SwiftNetworkProviderStrategy`

---

## 3. Why It Helps

- removes provider branching from core services
- makes unsupported capabilities explicit
- keeps tests focused on one provider contract at a time

---

## 4. AI Agent Directives

1. Use a `Strategy` when provider capabilities differ but the business intent is stable.
2. Keep strategy selection in the application layer or factory, not in the aggregate.
3. Do not leak provider DTOs across the strategy boundary.
