# QA Checklist — [Feature / PR]

> **Used during:** `/speckit.implement` completion, review, and handoff
> **Reviewer:** [AI Agent / Human]
> **Date:** YYYY-MM-DD

---

## 1. Code Correctness

- [ ] No hallucinated imports, packages, or APIs.
- [ ] Error paths are handled explicitly.
- [ ] Boundary conditions and off-by-one cases are covered.
- [ ] Business invariants from the plan/spec are enforced in code.

## 2. Test Quality

- [ ] Unit tests cover core domain rules and edge cases.
- [ ] Integration tests cover key persistence/integration boundaries.
- [ ] E2E tests exist for in-scope user journeys.
- [ ] Tests assert outcomes (state/events/contracts), not only execution.

## 3. Security

- [ ] No hard-coded secrets or credentials in code or tests.
- [ ] Input validation/sanitization is present at trust boundaries.
- [ ] Query construction avoids injection risks.
- [ ] Authentication/authorization checks are preserved for protected flows.
- [ ] OWASP-focused checks are covered for touched trust boundaries (injection, access control, SSRF/XSS where relevant).
- [ ] Rate-limiting protections are preserved or added for sensitive/public endpoints.

## 4. Observability

- [ ] Errors are logged with actionable context.
- [ ] Important domain events/metrics are emitted.
- [ ] Health/readiness checks are present where required.
- [ ] Logs avoid sensitive data exposure.

## 5. Performance and Scalability

- [ ] No obvious N+1 query patterns.
- [ ] No unbounded loops/collections on hot paths.
- [ ] Pagination/chunking is used for large result sets.
- [ ] Timeouts/retries are bounded and intentional.

## 6. Accessibility and UX (If Frontend)

- [ ] Keyboard and focus behavior remains usable.
- [ ] Semantic markup and labels are present.
- [ ] Error and loading states are visible and understandable.
- [ ] Core journeys are responsive and consistent.

## 7. Constitution Compliance

- [ ] SoC: responsibilities are cleanly separated.
- [ ] KISS: solution is no more complex than needed.
- [ ] YAGNI: no speculative abstractions.
- [ ] DRY with nuance: extraction only after repeating patterns emerge.
- [ ] SOLID: SRP and dependency inversion preserved where needed.

## 8. Review and Cleanup Overlays

- [ ] Review mode remains risk-first (severity-ordered findings) and does not implement new features.
- [ ] Cleanup mode remains evidence-driven and requests approval before destructive removals/upgrades.

---

_Template source: `presets/base/templates/qa-checklist-template.md`_
