"""Mutation adapter registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from mutation_adapters import cargo_mutants_adapter, generic_command_adapter, pitest_adapter, python_adapter, stryker_adapter


def run(adapter: str, workspace: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = adapter.strip().lower()
    if normalized == "generic":
        return generic_command_adapter.run(workspace, config)
    if normalized == "stryker":
        return stryker_adapter.run(workspace, config)
    if normalized == "pitest":
        return pitest_adapter.run(workspace, config)
    if normalized == "cargo-mutants":
        return cargo_mutants_adapter.run(workspace, config)
    if normalized == "python":
        return python_adapter.run(workspace, config)
    return {
        "tool": normalized or "unknown",
        "report": {},
        "exit_code": 0,
        "error": f"Unsupported mutation adapter '{adapter}'.",
    }

