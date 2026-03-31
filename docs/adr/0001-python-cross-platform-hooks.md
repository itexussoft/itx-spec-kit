# ADR 0001: Python for Cross-Platform Hooks

- Status: Accepted
- Date: 2026-03-25

## Context

The kit must run quality gates reliably across Windows and POSIX systems. Maintaining separate `.sh` and `.ps1` hook implementations for gate logic creates drift risk, duplicated maintenance, and inconsistent behavior.

## Decision

Implement hook executables in Python 3.x as the single cross-platform runtime for `itx-gates`.

Bootstrap scripts remain platform-native (`itx-init.sh` and `itx-init.ps1`), but gate logic and validators are Python-only.

## Consequences

- Positive:
  - One implementation path for gate behavior.
  - Better parity across supported agent environments.
  - Lower maintenance burden for validator evolution.
- Trade-offs:
  - Python 3.x is a hard host prerequisite.
  - Runtime dependency handling must remain lightweight and robust.

## Related Files

- `extensions/itx-gates/hooks/orchestrator.py`
- `extensions/itx-gates/hooks/validators/`
- `init-scripts/itx-init.sh`
- `init-scripts/itx-init.ps1`
