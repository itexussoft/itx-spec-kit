"""Generic command adapter for mutation reports."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List


def _normalize_command(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(part) for part in value if str(part).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def run(workspace: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    command = _normalize_command(config.get("command"))
    generic_cfg = config.get("generic") if isinstance(config.get("generic"), dict) else {}
    report_file = generic_cfg.get("report_file")
    if report_file is None:
        report_file = config.get("report_file")
    try:
        timeout_s = max(1, int(config.get("timeout_s", 120)))
    except (TypeError, ValueError):
        timeout_s = 120
    if not command:
        return {
            "tool": "generic",
            "report": {},
            "exit_code": 0,
            "error": "Generic mutation runner requires a non-empty 'command' list.",
        }

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
            "tool": "generic",
            "command": command,
            "report": {},
            "exit_code": 127,
            "error": f"Command binary not found: {exc}",
        }
    except subprocess.TimeoutExpired:
        return {
            "tool": "generic",
            "command": command,
            "report": {},
            "exit_code": 124,
            "error": f"Command timed out after {timeout_s}s.",
        }

    raw_text = result.stdout or ""
    if isinstance(report_file, str) and report_file.strip():
        candidate = workspace / report_file
        if candidate.exists():
            raw_text = candidate.read_text(encoding="utf-8", errors="ignore")
    if not raw_text.strip():
        return {
            "tool": "generic",
            "command": command,
            "report": {},
            "exit_code": result.returncode,
            "stdout": result.stdout or "",
            "stderr": result.stderr or "",
            "parse_error": "Empty mutation report output.",
        }

    parse_error: str | None = None
    report_payload: Dict[str, Any] = {}
    try:
        decoded = json.loads(raw_text)
        if isinstance(decoded, dict):
            report_payload = decoded
        elif isinstance(decoded, list):
            report_payload = {"schemaVersion": "1.0", "mutants": decoded}
        else:
            report_payload = {}
    except json.JSONDecodeError as exc:
        parse_error = str(exc)

    return {
        "tool": "generic",
        "command": command,
        "report": report_payload,
        "parse_error": parse_error,
        "exit_code": result.returncode,
        "stdout": result.stdout or "",
        "stderr": result.stderr or "",
    }
