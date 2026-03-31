# Feature Specification Template

## Problem
- What user or business problem is being solved?

## Scope
- In-scope:
- Out-of-scope:

## Requirements
- Functional:
- Non-functional:

## Code-Level Design Patterns

> **Mandatory.** Before writing implementation code, declare which code-level
> patterns from `.specify/design-patterns/` will be applied and why.

- **Design patterns to apply:**
  - [ ] Pattern name → rationale for using it in this feature.
- **Anti-patterns to guard against:**
  - [ ] Anti-pattern name → how the implementation will avoid it.

## Risks
- Technical:
- Compliance:

## Validation
- **E2E tests:** For each user journey in Scope, list the E2E test that will verify it.
  - [ ] Journey name -> expected test file, key assertion.
- **Integration tests:** List integration boundaries that need dedicated tests.
  - [ ] Boundary -> what is verified.
- **Unit tests:** Key domain logic scenarios.
  - [ ] Module/Aggregate -> scenarios.
- **Gate expectations:** Which gate rules this feature is expected to satisfy.
