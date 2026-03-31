# End-to-End Testing Strategy

> **Phase relevance:** Plan, Tasks, Implement
> **Supersedes:** Ad-hoc smoke testing and mock-heavy pseudo-E2E tests.

---

## 1. One E2E Test per User Journey

Every user journey declared in the feature Scope must map to at least one
named E2E test case.

**Rules for the AI agent:**

- Build a traceable mapping: `Scope journey -> E2E test file -> assertions`.
- If a journey has branching outcomes, keep one happy-path test and add focused
  failure-path tests.
- For Patch Plans, include at least one regression E2E or integration test for
  the changed behavior path.

---

## 2. Test the Contract, Not the Implementation

E2E tests validate externally observable behavior across component boundaries.

**Rules for the AI agent:**

- Assert request/response contracts, persisted state, and emitted integration
  events.
- Avoid asserting internal function calls, private methods, or class wiring.
- Keep assertions business-readable (status transitions, invariants, outcomes).

---

## 3. Use Real Infrastructure Boundaries

E2E tests are only credible when infrastructure boundaries behave like
production.

**Rules for the AI agent:**

- Use containers (Testcontainers or Docker Compose) for DBs, brokers, and caches
  when possible.
- Do not mock internal repositories or domain services in E2E tests.
- External third-party APIs may use contract stubs (for example WireMock) to
  keep tests deterministic and cost-effective.

---

## 4. Keep Tests Isolated and Order-Independent

Each test must set up and clean up its own data.

**Rules for the AI agent:**

- No shared mutable global state between E2E tests.
- No assumptions about execution order.
- Use fixture factories and explicit teardown (or transactional rollback) per
  test.

---

## 5. Make Time and Randomness Deterministic

Flaky tests usually come from uncontrolled clocks, randomness, or retries.

**Rules for the AI agent:**

- Inject clocks and ID generators where behavior depends on time/IDs.
- Seed randomness explicitly.
- Prefer polling with bounded retries/timeouts over unbounded sleeps.

---

## 6. Follow E2E Naming Conventions

The quality gate discovers E2E tests by filename patterns.

**Rules for the AI agent:**

- Python: `e2e_test_*.py`
- JavaScript/TypeScript: `*.e2e-spec.js`, `*.e2e-spec.ts`,
  `*.e2e.test.js`, `*.e2e.test.ts`
- Keep file names aligned with journey names for traceability.

---

## 7. Use Appropriate Assertion Granularity

Assertions should be strict where contracts matter and minimal where they do
not.

**Rules for the AI agent:**

- Happy path: assert full response contract and key persisted/event side effects.
- Failure path: assert error type/code and relevant invariant, not unrelated
  payload details.
- Avoid brittle snapshots for dynamic fields unless normalized first.

---

## 8. Bound Execution with Explicit Timeouts

Unbounded waits hide deadlocks and hang CI pipelines.

**Rules for the AI agent:**

- Define per-test or per-suite timeouts.
- Use bounded polling for async workflows.
- Fail fast with actionable diagnostics when expected events never arrive.

---

## Language-Idiomatic Examples

```python
def test_place_order_happy_path(api_client, order_repo, event_bus):
    response = api_client.post("/orders", json={"customerId": "C-1", "amount": "10.00"})
    assert response.status_code == 201
    assert order_repo.get(response.json()["id"]).status == "CONFIRMED"
    assert event_bus.has_event("OrderConfirmed")
```

```typescript
it("creates order and emits confirmation event", async () => {
  const res = await request(app).post("/orders").send({ customerId: "C-1", amount: "10.00" });
  expect(res.status).toBe(201);
  await expect(orderReadModel.get(res.body.id)).resolves.toMatchObject({ status: "CONFIRMED" });
  await expect(eventProbe.has("OrderConfirmed")).resolves.toBe(true);
});
```
