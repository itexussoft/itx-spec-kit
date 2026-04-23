# Itexus Base Constitution

## Core Delivery Rules

1. Follow the spec-driven workflow: constitution → feature specify or brownfield intake → clarify (feature flow only, optional) → plan → **tasks** → analyze (optional) → implement. **`/speckit.analyze` requires `tasks.md`** in the active workstream; run **`/speckit.tasks`** first.
1b. During `/speckit.tasks`, use `tasks-template.md` as the format reference. Every task item **must** use markdown checkbox syntax (`- [ ]`). During `/speckit.implement`, flip each checkbox to `- [x]` upon completion — do not remove or rewrite completed items.
2. Maintain test/cleanup/review discipline at the end of implementation. Run community extensions (`/speckit.review.run`, `/speckit.cleanup.run`) via the universal runner adapter — see `.cursor/rules/itx-speckit-commands.mdc`.
3. Prefer deterministic, auditable changes over opaque shortcuts.
4. Record assumptions and unresolved risks in project docs.
4b. Reference `docs/knowledge-base/index.md` for the knowledge base index, including workflow documentation and domain-selection guidance.
4c. Use progressive loading: read `.specify/context/execution-brief.md` first (when present), then load only files explicitly referenced by the brief. Open control-plane artifacts directly only when blocked, investigating gate feedback, or when a human requests it.
4d. Treat `.specify/context/execution-brief.md` as the active context snapshot for the current workstream. Do not introduce a second memory-bank lifecycle for this kit.
4e. Apply targeted micro-overlays only when relevant to the current plan scope: ACL for external integrations, security overlays (auth/secrets, OWASP, rate-limiting) for exposed trust boundaries, and TDD loop guidance for bugfix/refactor/modify-style changes.

## Architectural Design Requirements

5. During `/speckit.plan`, read `.specify/pattern-index.md` for the catalog of available patterns, design-patterns, and anti-patterns. Explicitly reference selected pattern filenames in the plan before implementation. In lazy knowledge mode, use a structured selection block (`<!-- selected_patterns: file.md, ... -->`) so the gate can materialize them, and read candidate pattern content from `.specify/.knowledge-store/` to inform selections.
6. During `/speckit.plan`, choose the policy-mapped artifact for the active work class:
   - `feature` -> `system-design-plan-template.md`
   - `patch` and `tooling` -> `patch-plan-template.md`
   - `refactor` -> `refactor-plan-template.md`
   - `bugfix` -> `bugfix-report-template.md`
   - `migration` -> `migration-plan-template.md`
   - `spike` -> `spike-note-template.md`
   - `modify` -> `modify-plan-template.md`
   - `hotfix` -> `hotfix-report-template.md`
   - `deprecate` -> `deprecate-plan-template.md`
7. Every **Full Plan** must explicitly name which DDD Bounded Contexts, Aggregates, and pattern files from `.specify/patterns/` the design relies on. If the design does not use a pattern, state why.
8. Record significant architectural decisions using the `architecture-decision-record-template.md` template and store them in `docs/adr/`.

## Code-Level Design Standards

9. For **Full Plan** features, after identifying Aggregates and Bounded Contexts, walk through the **Code-Level Pattern Selection Matrix** in Section 4b of the System Design Plan template. Evaluate every signal row against the feature requirements and mark each as Yes or No with a rationale. Section 4b is mandatory for Full Plan features.
10. For **Full Plan** features, when implementing business logic, strictly adhere to the Modern GoF and DDD principles defined in the `.specify/design-patterns/` directory. Only patterns marked **Yes** in System Design Plan Section 4b are expected — but all marked patterns are mandatory during the Tasks and Implement phases.
11. For **Full Plan** features, do not use outdated patterns such as manual Singletons, deep inheritance trees, the classic Visitor pattern, or the Template Method pattern. Consult `.specify/anti-patterns/` for the full list of forbidden and demoted patterns. Every anti-pattern marked **Guard** in Section 4b must have an explicit mitigation in the implementation.
12. For **Full Plan** features, before writing implementation code, the feature specification must explicitly declare which code-level design patterns from `.specify/design-patterns/` will be applied (see the "Code-Level Design Patterns" section of the spec template). These declarations must be consistent with Section 4b selections from the System Design Plan.
13. Replace all raw primitives (`string`, `int`, `float`) that carry domain meaning with Value Objects. Return `Result<T, E>` from operations that can fail for business reasons — reserve exceptions for infrastructure faults.

## Core AI Operating Principles (Timeless Foundations)

14. **Separation of Concerns:** Clear module boundaries are mandatory. You must ensure code is navigable by both humans and AI agents. Do not create "God Classes" or massive files that will overwhelm future context windows.
14b. **AI-First Readability:** Code must be understandable by an AI agent reading a single file in isolation. Maximize local reasoning: keep files under ~300 lines where practical, limit module hierarchy to two levels, and keep call depth from entry point to core logic shallow. See `.specify/patterns/cli-orchestrator-architecture.md` for details.
15. **KISS (Keep It Simple, Stupid):** As an AI, resist the temptation to over-engineer or generate massive enterprise boilerplates when a simple solution suffices. Simplicity is your primary defense against accidental complexity.
16. **YAGNI (You Aren't Gonna Need It):** Strictly resist speculative abstraction. Build exactly what is required for the current prompt/spec and nothing more. We will refactor when the pattern becomes clear in future iterations.
17. **DRY (Don't Repeat Yourself) with Nuance:** Premature DRY is worse than mild duplication. Do not extract shared code or create base classes prematurely. Strictly adhere to the **"Rule of Three"** before extracting shared logic.
18. **SOLID Principles:** Apply SOLID rigorously. Pay special attention to the **Single Responsibility Principle (SRP)** to keep context-window size manageable, and **Dependency Inversion (DI)** to ensure components can be isolated and tested easily.

**Execution Directive:** The AI agent must evaluate its own implementation plans against these 5 principles during the "Analyze" and "Plan" workflow phases. Any proposed architecture that violates KISS or YAGNI must be automatically rejected and simplified before moving to the "Tasks" phase.

For detailed rationale and examples, see `.specify/patterns/foundational-principles.md`.

## Testing Requirements

19. Every feature must include E2E tests for each user journey declared in the spec Scope. E2E tests must verify the full path from API entry to persistence and event publication where applicable.
20. E2E tests must use real infrastructure boundaries (containers or equivalent in-memory runtime dependencies) rather than mocking internal repositories and domain services. External third-party APIs may use contract stubs.
19b. For Tool Plan projects without API entrypoints, E2E tests must verify the CLI boundary: invoke the tool as a subprocess, assert exit codes, stdout/stderr diagnostics, and produced state/artifact files. Infrastructure containers are not required when dependencies are mocked at subprocess boundaries.
21. E2E test files must follow discoverable naming conventions: `e2e_test_*.py`, `*.e2e-spec.js`, `*.e2e-spec.ts`, `*.e2e.test.js`, or `*.e2e.test.ts`.
22. Each E2E test must be independent: no shared mutable state, no execution-order dependencies, and explicit setup/teardown (or transactional rollback) per test.
23. Patch Plan implementations must include at least one regression E2E or integration test that covers the changed behavior path.
24. For payment entrypoints, enforce idempotency-key handling and explicit auth/SCA boundaries. Do not update account balances in place; use append-only ledger entries.

## Quality Gate Alignment

- Respect active gate outcomes from `itx-gates`. Gate enforcement rules are defined in `.specify/policy.yml`.
- Treat Tier 1 failures as required auto-correction tasks.
- Treat Tier 2 failures as hard-stop events requiring human intervention.
- Treat heuristic Tier 1 findings as mandatory investigation items; they require explicit confirmation before any manual Tier 2 override/escalation decision.
- Treat active validators as deterministic tripwires, not full architectural or compliance proof.
- The `after_plan` gate validates that a plan exists and mandatory sections are populated (Full Plan: `4`, `4b`, `5`; Patch Plan: `1`, `2`).
- The `after_implement` gate validates E2E test presence and basic assertion quality via naming conventions and file-content checks.
- In `knowledge.mode: lazy`, `after_plan` also validates that selected pattern filenames are provided (for Full Plans) and resolvable.
- Patch Plans may declare `<!-- selected_patterns: none -->` to explicitly opt out of pattern selection.
- Pre-action audit logging is required only for high-risk actions (major refactor, package install/remove, high-risk ops/runtime changes).

## Delivery Mechanics

25. Use workstream-scoped branches. Preferred prefixes are `feature/<slug>`, `refactor/<slug>`, `bugfix/<slug>`, `hotfix/<slug>`, `deprecate/<slug>`, and `modify/<slug>` (or `modify/<parent-feature>-<slug>` when the behavior change is tightly tied to a delivered feature). Keep each branch aligned with a single approved workstream scope.
26. Use commit prefixes to communicate intent: `spec:`, `plan:`, `tasks:`, `impl:`, `test:`, `docs:`, `fix:`.
27. Create pull requests only after required gates pass and include traceability links (spec, plan, tasks, done report) plus test/gate evidence.
28. PR merges always require explicit human action. Agents must not auto-merge.
29. Treat PR review as a feedback loop: apply accepted comments, rerun affected checks, and log unresolved items/assumptions in delivery artifacts.
30. During review and cleanup phases, keep overlays lightweight and subordinate to existing `/speckit.review.run` and `/speckit.cleanup.run` flows. Do not introduce competing lifecycle commands.
