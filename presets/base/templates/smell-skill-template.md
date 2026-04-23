---
name: "<smell-id-lowercase>"
description: "Apply deterministic smell-to-refactoring guidance for <Smell Name>."
argument-hint: "rule_id=<linter-rule-id> file=<path> line=<line>"
allowed-tools:
  - read_file
  - search
  - edit_file
---

# Smell Skill

## Trigger
- Rule ID: `<rule-id>`
- Smell: `<Smell Name>`

## Refactoring Strategy
- Primary refactoring: `<refactoring-id>`
- Intent: `<intent>`
- Secondary option: `<refactoring-id>`

## Test-First Guardrail
- Strategy: `<strategy>`
- Hint: `<hint>`

## Safety Rules
- Keep behavior equivalent unless the plan explicitly requests behavior changes.
- Limit the first pass to one cohesive extraction/move.
- Run focused tests before and after each structural change.

## Output Contract
- List changed files.
- Explain how the smell signal maps to the chosen refactoring.
- Include verification steps and any residual risk.
