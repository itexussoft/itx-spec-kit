# Delivery Mechanics

## Branching Strategy

- Create one branch per feature using `feature/<slug>`.
- Keep branch scope aligned with a single approved spec/plan.
- Avoid mixing unrelated fixes into the same feature branch.

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
