# Delivery Mechanics

## Branching Strategy

- Create one branch per active workstream.
- Recommended prefixes:
  - `feature/<slug>` for net-new capability
  - `refactor/<slug>` for behavior-preserving cleanup
  - `bugfix/<slug>` for defect correction
  - `hotfix/<slug>` for urgent incident response
  - `deprecate/<slug>` for phased sunset/removal work
  - `modify/<slug>` or `modify/<parent-feature>-<slug>` for behavior changes
- Keep branch scope aligned with a single approved workstream and plan.
- Avoid mixing unrelated fixes into the same workstream branch.

## Commit Conventions

- Use intent-first prefixes:
  - `spec:` specification-only updates
  - `plan:` planning/design updates
  - `tasks:` task breakdown updates
  - `impl:` implementation changes
  - `test:` test additions/updates
  - `docs:` documentation updates
  - `fix:` corrective changes discovered during gates/review
- Keep commit messages concise and traceable to requirement IDs when available.

## Pull Request Creation Rules

- Open a PR only after implementation and completion gates pass.
- Include links to spec, plan, tasks, and done report artifacts.
- Include gate outcomes and test evidence in the PR body.

## Merge Policy (Human Required)

- PR merge authority is always human.
- Agents must not auto-merge, even when all gates pass.
- Human override decisions must be logged with rationale.

## PR Review Feedback Loop

- On review comments, agent classifies each item as:
  - accepted-change
  - clarification-request
  - disagreement-needs-human
- Apply accepted changes, rerun impacted checks, and push updates.
- Record unresolved items in done report "Outstanding Items".
