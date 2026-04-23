"""Spectral adapter for architecture contract checks."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List

from architecture_parsers.sarif import parse_sarif_text


def _normalize_files(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def run(workspace: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    spectral_cfg = config.get("spectral") if isinstance(config.get("spectral"), dict) else {}
    try:
        timeout_s = max(1, int(config.get("timeout_s", 120)))
    except (TypeError, ValueError):
        timeout_s = 120
    explicit = spectral_cfg.get("command")
    command: List[str]
    if isinstance(explicit, list) and explicit:
        command = [str(part) for part in explicit if str(part).strip()]
    else:
        files = _normalize_files(spectral_cfg.get("files") or config.get("files"))
        if not files:
            return {
                "tool": "spectral",
                "violations": [],
                "exit_code": 0,
                "error": "Spectral adapter requires 'spectral.files' or an explicit 'spectral.command'.",
            }
        command = ["spectral", "lint", "-f", "sarif", "--fail-severity=none", *files]

    try:
        result = subprocess.run(
            command,
            cwd=str(workspace),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except FileNotFoundError as exc:
        return {
            "tool": "spectral",
            "command": command,
            "violations": [],
            "exit_code": 127,
            "error": f"Spectral binary not found: {exc}",
        }
    except subprocess.TimeoutExpired:
        return {
            "tool": "spectral",
            "command": command,
            "violations": [],
            "exit_code": 124,
            "error": f"Spectral command timed out after {timeout_s}s.",
        }

    parsed: List[Dict[str, Any]] = []
    parse_error: str | None = None
    if (result.stdout or "").strip():
        try:
            parsed = parse_sarif_text(result.stdout or "")
        except Exception as exc:  # noqa: BLE001
            parse_error = str(exc)

    return {
        "tool": "spectral",
        "command": command,
        "violations": parsed,
        "parse_error": parse_error,
        "exit_code": result.returncode,
        "stdout": result.stdout or "",
        "stderr": result.stderr or "",
    }
