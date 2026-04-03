# SaaS Platform Constraints

- Reject cross-tenant data access without explicit tenant context verification at the boundary.
- Require tenant ID propagation through every service boundary (HTTP headers, message metadata, job arguments).
- Design token and feature flag resolution must be cacheable per tenant with explicit TTL and invalidation strategy.
