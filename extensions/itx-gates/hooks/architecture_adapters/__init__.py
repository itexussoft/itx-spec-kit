"""Architecture adapter registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from architecture_adapters import archunit_adapter, generic_command_adapter, modulith_adapter, spectral_adapter


def run(adapter: str, workspace: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = adapter.strip().lower()
    if normalized == "generic":
        return generic_command_adapter.run(workspace, config)
    if normalized == "spectral":
        return spectral_adapter.run(workspace, config)
    if normalized == "archunit":
        return archunit_adapter.run(workspace, config)
    if normalized == "modulith":
        return modulith_adapter.run(workspace, config)
    return {
        "tool": normalized or "unknown",
        "violations": [],
        "exit_code": 0,
        "error": f"Unsupported architecture adapter '{adapter}'.",
    }

