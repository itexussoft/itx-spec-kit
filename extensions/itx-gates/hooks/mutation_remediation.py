"""Behavior-focused remediation hints for mutation findings."""

from __future__ import annotations

from typing import Dict


_MUTATOR_HINTS: Dict[str, str] = {
    "conditionalexpression": (
        "A boundary condition flipped and no test failed. Add a test at the exact boundary value, not only obvious in/out values."
    ),
    "equalityoperator": (
        "An equality boundary changed and passed. Add assertions for exact equality and off-by-one neighbors."
    ),
    "mathop": (
        "Arithmetic behavior changed without detection. Add assertions on exact computed values, not only types or truthiness."
    ),
    "returnvalue": (
        "A return value changed but tests still passed. Assert concrete expected values instead of shape-only checks."
    ),
    "booleanreturn": (
        "Boolean return behavior flipped. Add assertions that verify both true and false branches."
    ),
    "voidmethodcalls": (
        "A side-effecting call was removed. Assert observable side effects such as state change, persistence, or collaborator calls."
    ),
    "removecall": (
        "A collaborator call was removed. Verify arguments and outcomes caused by the call, not only top-level function return."
    ),
}


def remediation_for(mutator_name: str, status: str) -> str:
    normalized_mutator = mutator_name.strip().lower()
    normalized_status = status.strip().lower()
    if normalized_status == "nocoverage":
        return "The mutated line has no covering test. Add a test that executes this path before tuning assertions."
    for key, hint in _MUTATOR_HINTS.items():
        if key in normalized_mutator:
            return hint
    return "Strengthen tests around the mutated behavior with assertions on concrete outcomes and side effects."

