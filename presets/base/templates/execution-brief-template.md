---
schema_version: "1.0"
feature: "<feature-slug>"
work_class: "<feature|patch|refactor|bugfix|migration|tooling|spike>"
domain: "<base|fintech-trading|fintech-banking|healthcare|saas-platform>"
knowledge_mode: "<lazy|eager>"
generated_from:
  - "plan"
  - "tasks"
  - "gate_feedback"
generated_at: "YYYY-MM-DDTHH:MM:SS+00:00"
---

# Execution Brief

## Behavior Overlay
- Think Before Coding: restate objective, constraints, verification target.
- Simplicity First: choose the smallest change that satisfies the brief.
- Surgical Changes: stay within listed scope and avoid unrelated edits.
- Goal-Driven Execution: verify against named tests and gate signals.

## Objective
- <1-3 concise bullets>

## Scope
- In: <what is in scope>
- Out: <what is out of scope>

## Files/Modules In Scope
- <max 10 entries>

## Selected Patterns To Load
- <pattern-file.md | none>

## Targeted Micro-Overlays
- <ACL / security / TDD overlays only when relevant to this plan>

## Active Context
- This execution brief is the active context snapshot for the current workstream.
- <working assumptions and open questions, when present>

## Constraints and Invariants
- <max 8 bullets>

## Active Risks and Gate Signals
- <max 5 bullets, concise summary only>

## Verification Targets
- <tests to preserve and/or add>

## Next Actions
- <unchecked task or next minimal action>

## Human Approval Required
- <only when active human hold exists>
