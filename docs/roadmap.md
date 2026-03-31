# itexus-spec-kit Roadmap

This roadmap is status-driven and reflects work already completed in `0.1.3`.

## Completed Baseline (Shipped)

### E2E and QA foundation

- Added baseline E2E test enforcement in `after_implement` gate:
  - file discovery by naming convention
  - assertion-presence checks
- Added mandatory `## 13. Test Strategy` section for Full Plans.
- Added testing and QA artifacts in base preset:
  - `patterns/e2e-testing-strategy.md`
  - `templates/test-strategy-template.md`
  - `templates/qa-checklist-template.md`
- Updated constitution and KB docs to align with test-first implementation flow.
- Added explicit rule-to-control matrix and assurance-boundary guidance in docs.

### Acceptance signals (met)

- Orchestrator tests cover E2E missing/present/empty scenarios.
- Full test suite and build pipeline pass in CI/local.
- Release artifacts generated successfully.

---

## Milestone 1: Gate Engine Hardening

Priority: High  
Status: Planned (Next)

### Goals

- Expand trading validator from heuristic checks to broader AST coverage (Python + TypeScript parsing strategy).
- Reduce false positives in healthcare log scanning with context-aware matching.
- Publish an explicit rule-to-tier severity matrix to avoid misclassification.
- Add validator diagnostics that explain remediation steps per rule.
- Introduce per-rule confidence metadata and remediation ownership for faster triage.
- Align retry escalation behavior so heuristic findings do not auto-halt by default.

### Acceptance signals

- Additional unit tests for each validator branch and edge case.
- Documented rule-to-tier matrix in gate docs.
- Stable test pass rate across local and CI runs.
- Reduced false-positive rate in sample benchmark repos.

---

## Milestone 2: Upstream Drift E2E Matrix

Priority: High  
Status: Planned

### Goals

- Extend scheduled drift workflow from smoke clone to executable compatibility checks.
- Validate bootstrap + gate flow against latest `github/spec-kit` main and a pinned known-good baseline.
- Detect template signature changes that can break overrides/bootstrap flow.
- Fail release packaging when drift checks fail.

### Acceptance signals

- Scheduled CI job executes bootstrap + hook flow successfully on both targets.
- Drift report includes pass/fail summary with actionable diff hints.
- Failing drift checks block release packaging.

---

## Milestone 3: Bootstrap UX and Reliability

Priority: Medium  
Status: Planned

### Goals

- Add clearer preflight diagnostics for missing host dependencies.
- Improve init script error handling around failed extension installs.
- Add optional non-interactive mode profiles for CI bootstrap testing.
- Improve parity validation between shell and PowerShell init paths.

### Acceptance signals

- Bootstrap failure paths tested in CI.
- Error messages map to actionable fixes.
- Platform parity checks pass for shell and PowerShell scripts.

---

## Milestone 4: Packaging and Distribution

Priority: Medium  
Status: Planned

### Goals

- Add artifact metadata fields for remote URLs/checksums in catalog.
- Validate generated zips with structural checks before publish.
- Add release notes generator from manifests and ADR changes.
- Provide a single-command release checklist workflow.

### Acceptance signals

- `dist/` artifacts include checksum manifest.
- Catalog references and checksums validated in CI.
- Release checklist fully automated from one command.

---

## Milestone 5: Banking LLM-Judge Integration

Priority: Medium  
Status: Discovery / Pilot

### Goals

- Introduce pluggable judge adapter interface (provider-agnostic).
- Define prompt contract and deterministic fallback strategy.
- Support offline/no-LLM mode with explicit warning semantics.
- Roll out behind a feature flag with safe default disabled.

### Acceptance signals

- Integration tests for adapter success/failure paths.
- Contract tests for prompt inputs/outputs.
- Tier 2 behavior verified for critical PCI/PSD2 findings.
- Cost/latency budget documented and validated in pilot repos.
